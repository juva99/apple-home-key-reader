import argparse
import json
import logging
import signal
import sys

from pyhap.accessory_driver import AccessoryDriver

from accessory import Lock
from repository import Repository
from service import Service
from remote_service import RemoteUnlockService
from util.bfclf import BroadcastFrameContactlessFrontend

# By default, this file is located in the same folder as the project
CONFIGURATION_FILE_PATH = "configuration.json"


def load_configuration(path=CONFIGURATION_FILE_PATH) -> dict:
    return json.load(open(path, "r+"))


def parse_arguments():
    parser = argparse.ArgumentParser(description="Apple Home Key Reader")
    parser.add_argument(
        "--pair", 
        action="store_true", 
        help="Enable pair mode for device pairing"
    )
    return parser.parse_args()


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


def configure_remote_unlock_service(config: dict, lock_accessory=None):
    """Configure the remote unlock service if enabled"""
    remote_config = config.get("remote_unlock", {})
    
    if not remote_config.get("enabled", False):
        logging.getLogger().info("Remote unlock service is disabled")
        return None
    
    try:
        service = RemoteUnlockService(
            supabase_url=remote_config["supabase_url"],
            supabase_anon_key=remote_config["supabase_anon_key"],
            lock_id=remote_config.get("lock_id", "front-door"),
            lock_accessory=lock_accessory
        )
        logging.getLogger().info("Remote unlock service configured")
        return service
    except KeyError as e:
        logging.getLogger().error(f"Missing remote unlock configuration: {e}")
        return None
    except Exception as e:
        logging.getLogger().error(f"Failed to configure remote unlock service: {e}")
        return None


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


def main(pair_mode = False):
    config = load_configuration()
    log = configure_logging(config["logging"])

    nfc_device = configure_nfc_device(config["nfc"])
    homekey_service = configure_homekey_service(config["homekey"], nfc_device)
    hap_driver, lock = configure_hap_accessory(config["hap"], homekey_service)

    # Configure remote unlock service after lock is created
    remote_unlock_service = configure_remote_unlock_service(config, lock_accessory=lock)

    if pair_mode:
        lock.setup_message()

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(
            s,
            lambda *_: (
                log.info(f"SIGNAL {s}"),
                homekey_service.stop(),
                remote_unlock_service.stop() if remote_unlock_service else None,
                hap_driver.stop(),
            ),
        )

    homekey_service.start()
    
    # Start remote unlock service if configured
    if remote_unlock_service:
        remote_unlock_service.start()
    
    hap_driver.start()


if __name__ == "__main__":
    args = parse_arguments()
    main(pair_mode=args.pair)
