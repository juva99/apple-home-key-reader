import asyncio
import logging
import socket
from operator import attrgetter

from zeroconf.asyncio import AsyncZeroconf

from pyhap.accessory_driver import AccessoryMDNSServiceInfo

from util.threads import create_runner

log = logging.getLogger()


def detect_local_address():
    """Return the primary local IPv4 address, or ``None`` when the network is down.

    No packets are actually sent: connecting a UDP socket only resolves the
    route/interface the kernel would use. When there is no usable route (e.g.
    the router rebooted) this raises ``OSError`` (``Network is unreachable``),
    which we translate into ``None``.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


class HapWatchdog:
    """Keeps the HomeKit accessory discoverable after network disruptions.

    pyhap relies on python-zeroconf, which binds its UDP sockets to the
    interface that was up when the driver started. If the network drops (e.g.
    the router reboots) those sockets become invalid and zeroconf keeps failing
    with ``Network is unreachable`` without ever rebinding, so the accessory
    silently becomes undiscoverable until the process is restarted.

    Two signals are used to decide when to rebuild the advertisement:

    1. HAP connections (primary): a HomeKit home hub (Apple TV / HomePod) keeps
       a persistent HAP/TCP connection open with the accessory. We read these
       live connections straight from ``driver.http_server.connections``. If
       every connection drops and does not come back within a short grace
       period, the advertisement is rebuilt so the hub can rediscover and
       reconnect. This directly reflects HomeKit reachability and ignores
       internet outages that do not affect the local network.
    2. Local network address (fallback): used only when no hub connection is
       currently keeping us engaged. It covers setups without a home hub and IP
       changes (DHCP) by rebuilding the advertisement when connectivity returns
       or the local IP changes.

    In both cases the remediation is identical: rebuild the (stuck) zeroconf
    advertiser so mDNS works on the live interface again.
    """

    def __init__(self, driver, check_interval: float = 15.0, grace_period: int = 2):
        self.driver = driver
        self.check_interval = max(1.0, float(check_interval))
        # Consecutive zero-connection checks tolerated before we assume HAP
        # connectivity was lost and re-publish the advertisement.
        self.grace_checks = max(1, int(grace_period))
        self._run_flag = True
        self._runner = None
        self._had_connection = False
        self._zero_streak = 0
        self._last_address = None

    def start(self):
        # Seed with the current address so a clean start does not trigger a
        # spurious fallback refresh on the very first check.
        self._last_address = detect_local_address()
        self._runner = create_runner(
            name="hap-watchdog",
            target=self.run,
            flag=attrgetter("_run_flag"),
            delay=self.check_interval,
            exception_delay=self.check_interval,
            start=True,
        )
        log.info(
            f"HAP watchdog started (interval={self.check_interval}s, "
            f"grace={self.grace_checks} checks)"
        )

    def stop(self):
        self._run_flag = False
        if self._runner is not None:
            self._runner.join()

    def run(self):
        # Primary: react to the HomeKit (HAP) connection state. While a hub is
        # connected this fully owns the decision; the network fallback only runs
        # when nothing is keeping us connected.
        if self._check_hap_connections():
            return
        self._check_network_address()

    def _active_connections(self) -> int:
        """Number of live HAP/TCP connections to HomeKit controllers."""
        server = getattr(self.driver, "http_server", None)
        connections = getattr(server, "connections", None) or {}
        try:
            return len(connections)
        except Exception:
            return 0

    def _check_hap_connections(self) -> bool:
        """Handle the HAP-connection signal.

        Returns ``True`` when the HAP signal is in charge this cycle (a hub is
        or was connected), meaning the network fallback should be skipped.
        """
        count = self._active_connections()
        log.debug(f"HAP watchdog check: {count} active HAP connection(s)")

        if count > 0:
            if not self._had_connection:
                log.info(
                    f"HomeKit controller connected ({count} active HAP connection(s))"
                )
            self._had_connection = True
            self._zero_streak = 0
            return True

        if not self._had_connection:
            # No hub has ever connected; nothing to recover from here. Let the
            # network fallback take over.
            return False

        self._zero_streak += 1
        if self._zero_streak == self.grace_checks:
            log.warning(
                "Lost all HomeKit (HAP) connections; re-publishing mDNS so "
                "controllers can reconnect"
            )
        if self._zero_streak < self.grace_checks:
            return True

        if self._refresh_advertisement(self._current_addresses()):
            # Wait for a controller to reconnect before arming again.
            self._had_connection = False
            self._zero_streak = 0
        return True

    def _check_network_address(self):
        """Fallback signal for hub-less setups and DHCP address changes."""
        address = detect_local_address()

        if address is None:
            if self._last_address is not None:
                log.warning(
                    "Network connectivity lost; will re-publish mDNS once it returns"
                )
            self._last_address = None
            return

        if address == self._last_address:
            return

        if self._last_address is None:
            log.info(
                f"Network connectivity restored (address {address}); "
                "re-publishing mDNS advertisement"
            )
        else:
            log.info(
                f"Local address changed {self._last_address} -> {address}; "
                "re-publishing mDNS advertisement"
            )

        if self._refresh_advertisement([address]):
            self._last_address = address

    def _current_addresses(self):
        """Best-effort current address list for the rebuilt advertisement."""
        address = detect_local_address()
        if address is not None:
            return [address]
        # Network still down: fall back to whatever the driver currently knows.
        return list(getattr(self.driver.state, "addresses", []) or [])

    def _refresh_advertisement(self, addresses) -> bool:
        if not addresses:
            log.warning("No usable address available; deferring mDNS refresh")
            return False

        loop = getattr(self.driver, "loop", None)
        if loop is None or not loop.is_running():
            log.warning(
                "HAP driver event loop is not running yet; deferring mDNS refresh"
            )
            return False

        future = asyncio.run_coroutine_threadsafe(
            self._async_refresh_advertisement(addresses), loop
        )
        try:
            future.result(timeout=30)
            return True
        except Exception:
            log.exception("Failed to re-publish mDNS advertisement")
            return False

    async def _async_refresh_advertisement(self, addresses):
        driver = self.driver
        old_advertiser = driver.advertiser
        old_service_info = driver.mdns_service_info

        # Point the advertisement at the current address(es). The IP may have
        # changed (DHCP) while the network was down.
        driver.state.addresses = addresses

        # Tear down the stale advertiser whose sockets are bound to the
        # interface that went away. Both calls are best-effort: the old sockets
        # may already be broken.
        if old_advertiser is not None:
            try:
                if old_service_info is not None:
                    await old_advertiser.async_unregister_service(old_service_info)
            except Exception:
                log.debug("Could not unregister stale mDNS service", exc_info=True)
            try:
                await old_advertiser.async_close()
            except Exception:
                log.debug("Could not close stale zeroconf advertiser", exc_info=True)

        # Recreate the advertiser so zeroconf rebinds to the live interface.
        zc_args = {}
        if driver.interface_choice is not None:
            zc_args["interfaces"] = driver.interface_choice
        driver.advertiser = AsyncZeroconf(**zc_args)
        driver.mdns_service_info = AccessoryMDNSServiceInfo(
            driver.accessory, driver.state, driver.zeroconf_server
        )
        await driver.advertiser.async_register_service(
            driver.mdns_service_info, cooperating_responders=True
        )
        log.info("mDNS advertisement re-published successfully")
