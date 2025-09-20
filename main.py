import argparse
import json
import logging
import signal
import sys

from pyhap.accessory_driver import AccessoryDriver

from accessory import Lock
from repository import Repository
from service import Service
from util.bfclf import BroadcastFrameContactlessFrontend

# By default, this file is located in the same folder as the project
CONFIGURATION_FILE_PATH = "configuration.json"


def load_configuration(path=CONFIGURATION_FILE_PATH) -> dict:
    return json.load(open(path, "r+"))


def configure_logging(config: dict):
    log = logging.getLogger()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)8s] %(module)-18s:%(lineno)-4d %(message)s"
    )
    hdlr = logging.StreamHandler(sys.stdout)
    log.setLevel(config.get("level", logging.INFO))
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    return log


def configure_hap_accessory(config: dict, homekey_service=None):
    driver = AccessoryDriver(port=config["port"], persist_file=config["persist"])
    print(config)
    print(f"gpio pin: {config.get('gpio', {}).get('pin', None)}")
    accessory = Lock(
        driver,
        "NFC Lock",
        service=homekey_service,
        lock_state_at_startup=int(config.get("default") != "unlocked"),
        gpio_pin=config.get("gpio", {}).get("pin", None),
    )
    driver.add_accessory(accessory=accessory)
    return driver, accessory


def configure_nfc_device(config: dict):
    clf = BroadcastFrameContactlessFrontend(
        path=config.get("path", None)
        or f"tty:{config.get('port')}:{config.get('driver')}",
        broadcast_enabled=config.get("broadcast", True),
    )
    return clf


def configure_homekey_service(config: dict, nfc_device, repository=None):
    service = Service(
        nfc_device,
        repository=repository or Repository(config["persist"]),
        express=config.get("express", True),
        finish=config.get("finish"),
        flow=config.get("flow"),
        # Poll no more than ~6 times a second by default
        throttle_polling=float(config.get("throttle_polling") or 0.15),
        lock_timeout=int(config.get("lock_timeout", 10)),
    )
    return service


def pair_mode(timeout=60):
    """Run in pairing mode to connect new HomeKit devices"""
    config = load_configuration()
    log = configure_logging(config["logging"])

    log.info("Starting HomeKit pairing mode...")

    nfc_device = configure_nfc_device(config["nfc"])
    homekey_service = configure_homekey_service(config["homekey"], nfc_device)

    # Create a temporary HAP accessory to display QR code and pairing info
    hap_driver, _ = configure_hap_accessory(config["hap"], homekey_service)

    print("\n🔗 HomeKit Pairing Mode Active")
    print("=" * 50)
    print("The HomeKit accessory is now discoverable!")
    print("You can add it to your Home app using the QR code above.")
    print(f"Pairing will timeout in {timeout} seconds.")
    print("Present your device to the NFC reader to complete setup.")
    print("=" * 50)

    try:
        # Start HAP driver to show QR code
        hap_driver.start()

        # Run NFC pairing
        success = homekey_service.pair_new_device(timeout_seconds=timeout)

        # Stop HAP driver
        hap_driver.stop()

        if success:
            print("✅ Successfully paired new HomeKit device!")
            return 0
        else:
            print("❌ Pairing timeout - no device was paired")
            return 1
    except Exception as e:
        log.error(f"Pairing failed: {e}")
        print(f"❌ Pairing failed: {e}")
        # Ensure HAP driver is stopped on error
        try:
            hap_driver.stop()
        except:
            pass
        return 1


def main_service():
    """Run the main HomeKit service (normal operation)"""
    config = load_configuration()
    log = configure_logging(config["logging"])

    nfc_device = configure_nfc_device(config["nfc"])
    homekey_service = configure_homekey_service(config["homekey"], nfc_device)
    hap_driver, _ = configure_hap_accessory(config["hap"], homekey_service)

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(
            s,
            lambda *_: (
                log.info(f"SIGNAL {s}"),
                homekey_service.stop(),
                hap_driver.stop(),
            ),
        )

    homekey_service.start()
    hap_driver.start()


def main():
    parser = argparse.ArgumentParser(description="Apple HomeKey Reader")
    parser.add_argument(
        "--pair",
        action="store_true",
        help="Enter pairing mode to connect new HomeKit devices",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Pairing timeout in seconds (default: 60)",
    )

    args = parser.parse_args()

    if args.pair:
        return pair_mode(timeout=args.timeout)
    else:
        main_service()


if __name__ == "__main__":
    sys.exit(main())
