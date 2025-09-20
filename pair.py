#!/usr/bin/env python3
"""
Convenience script to pair new HomeKit devices.
Usage: python pair.py [--timeout SECONDS]
"""

import argparse
import sys
from main import pair_mode


def main():
    parser = argparse.ArgumentParser(
        description="Pair new HomeKit devices with the Apple HomeKey Reader"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Pairing timeout in seconds (default: 60)",
    )

    args = parser.parse_args()

    print("🔗 HomeKit Device Pairing Tool")
    print("=" * 40)
    print(f"Pairing timeout: {args.timeout} seconds")
    print("A QR code will be displayed for HomeKit setup.")
    print("You can scan it with your Home app or present your")
    print("device to the NFC reader to complete pairing.")
    print("Press Ctrl+C to cancel")
    print()

    try:
        return pair_mode(timeout=args.timeout)
    except KeyboardInterrupt:
        print("\n❌ Pairing cancelled by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
