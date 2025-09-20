#!/usr/bin/env python3
"""
HomeKit Re-Pairing Script for Apple HomeKey Reader

This script allows you to pair new HomeKit devices (iPhones, iPads, etc.)
to your Apple HomeKey Reader even when the hap.state file already exists.

Usage:
    python example_pairing_usage.py [options]

Options:
    --timeout SECONDS    Pairing timeout in seconds (default: 300)
    --config PATH        Path to configuration file (default: configuration.json)
    --no-qr             Don't display QR code and setup information
    --duration SECONDS   How long to keep pairing mode active (default: 600)
    --control-point      Test control point pairing commands
    --status             Just show current pairing status
"""

import argparse
import json
import logging
import sys
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)8s] %(module)s:%(lineno)d %(message)s'
)
log = logging.getLogger()

def load_configuration(config_path="configuration.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"Configuration file '{config_path}' not found")
        print(f"❌ Configuration file '{config_path}' not found")
        print("Please ensure the configuration file exists or specify the correct path with --config")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in configuration file: {e}")
        print(f"❌ Invalid JSON in configuration file: {e}")
        sys.exit(1)

def setup_components(config):
    """Set up NFC device, repository, service, and accessory components"""
    from repository import Repository
    from service import Service
    from accessory import Lock
    from util.bfclf import BroadcastFrameContactlessFrontend
    from pyhap.accessory_driver import AccessoryDriver
    
    # Configure NFC device
    nfc_device = BroadcastFrameContactlessFrontend(
        path=config.get("nfc", {}).get("path", None) or 
             f"tty:{config.get('nfc', {}).get('port')}:{config.get('nfc', {}).get('driver')}",
        broadcast_enabled=config.get("nfc", {}).get("broadcast", True),
    )
    
    # Create repository and service
    repository = Repository(config["homekey"]["persist"])
    service = Service(
        clf=nfc_device,
        repository=repository,
        express=config.get("homekey", {}).get("express", True),
        finish=config.get("homekey", {}).get("finish", "silver"),
        flow=config.get("homekey", {}).get("flow", "fast"),
        throttle_polling=float(config.get("homekey", {}).get("throttle_polling", 0.15)),
        lock_timeout=int(config.get("homekey", {}).get("lock_timeout", 10)),
    )
    
    # Create HAP driver and accessory
    driver = AccessoryDriver(
        port=config["hap"]["port"], 
        persist_file=config["hap"]["persist"]
    )
    
    accessory = Lock(
        driver,
        "NFC Lock",
        service=service,
        lock_state_at_startup=int(config.get("hap", {}).get("default") != "unlocked"),
        gpio_pin=config.get("hap", {}).get("gpio", {}).get("pin", None),
    )
    
    # Set up the reference between service and accessory
    service.set_accessory_reference(accessory)
    driver.add_accessory(accessory=accessory)
    
    return nfc_device, service, driver, accessory

def show_pairing_status(service):
    """Show current pairing mode status and information"""
    print("\n📊 Current Pairing Status")
    print("=" * 50)
    
    is_active = service.is_pairing_mode_active()
    print(f"🔄 Pairing Mode Active: {'Yes' if is_active else 'No'}")
    
    pairing_info = service.get_pairing_info()
    if pairing_info:
        print(f"📋 Setup Code: {pairing_info['formatted_setup_code']}")
        print(f"🔗 QR URI: {pairing_info['qr_uri']}")
        print("💡 Ready to pair new devices")
    else:
        print("ℹ️ Device is already paired - use pairing mode to add more controllers")
    
    print("=" * 50)

def pair_new_device(service, driver, timeout_seconds, show_qr, duration_seconds):
    """Main pairing function"""
    print(f"\n🚀 Starting HomeKit Re-Pairing Session")
    print("=" * 60)
    print(f"⏱️ Pairing timeout: {timeout_seconds} seconds")
    print(f"🔄 Pairing mode duration: {duration_seconds} seconds")
    print(f"📱 Show QR code: {'Yes' if show_qr else 'No'}")
    print("=" * 60)
    
    try:
        # Check if device is configured
        if hasattr(service, 'repository'):
            reader_key = service.repository.get_reader_private_key()
            if reader_key in (None, b"", bytes.fromhex("00" * 32)):
                print("❌ Device is not configured via HAP")
                print("💡 Please run the initial setup first using: python main.py --pair")
                return False
        
        print("\n🔗 Enabling pairing mode...")
        success = service.enable_pairing_mode(duration_seconds, show_pairing_info=show_qr)
        
        if not success:
            print("❌ Failed to enable pairing mode")
            return False
        
        print(f"✅ Pairing mode enabled for {duration_seconds} seconds")
        
        if show_qr:
            print("\n💡 Use the QR code or setup code above to pair with HomeKit")
        
        print(f"\n⏳ Waiting {timeout_seconds} seconds for HomeKit device to pair...")
        print("📱 Open the Home app and add this accessory now!")
        print("🏠 You can also present an NFC device to complete the pairing")
        print("\n⚠️  Press Ctrl+C to cancel")
        
        # Start the pairing session
        start_time = time.time()
        success = service.pair_new_device(
            timeout_seconds=timeout_seconds, 
            enable_pairing_mode=False,  # Already enabled above
            show_pairing_info=False     # Already shown above
        )
        
        elapsed = time.time() - start_time
        
        if success:
            print(f"\n✅ Successfully paired new HomeKit device in {elapsed:.1f} seconds!")
            print("🎉 The new device can now control your HomeKey lock")
            print("� Check the Home app to confirm the device was added")
            return True
        else:
            print(f"\n⏰ Pairing timeout after {elapsed:.1f} seconds")
            print("❌ No device was paired")
            print("\n💡 Troubleshooting tips:")
            print("   - Ensure the Home app is open and ready")
            print("   - Check that you're on the same WiFi network")
            print("   - Try scanning the QR code again")
            print("   - Make sure the setup code was entered correctly")
            return False
            
    except KeyboardInterrupt:
        print("\n\n🛑 Pairing cancelled by user")
        return False
    except Exception as e:
        log.error(f"Pairing failed: {e}")
        print(f"\n❌ Pairing failed: {e}")
        return False
    finally:
        # Ensure pairing mode is disabled
        if service.is_pairing_mode_active():
            print("\n🔄 Disabling pairing mode...")
            service.disable_pairing_mode()

def test_control_point_commands(service):
    """Test HomeKit control point pairing commands"""
    print("\n🧪 Testing HomeKit Control Point Commands")
    print("=" * 50)
    
    # Simulate control point commands
    print("1. Testing enable pairing mode command...")
    # This would normally come from HomeKit app
    test_enable_cmd = bytes([0xFF, 0x01, 0x2C])  # Enable for 300 seconds
    print(f"   Command: {test_enable_cmd.hex()}")
    print("   Result: Would enable pairing mode for 300 seconds")
    
    print("\n2. Testing disable pairing mode command...")
    test_disable_cmd = bytes([0x00])
    print(f"   Command: {test_disable_cmd.hex()}")
    print("   Result: Would disable pairing mode")
    
    print("\n💡 These commands can be sent via HomeKit app's Lock Control Point")
    print("=" * 50)

def main():
    """Main script entry point"""
    parser = argparse.ArgumentParser(
        description="HomeKit Re-Pairing Script for Apple HomeKey Reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python example_pairing_usage.py                    # Standard pairing with defaults
    python example_pairing_usage.py --timeout 120     # Pair with 2 minute timeout
    python example_pairing_usage.py --no-qr           # Pair without showing QR code
    python example_pairing_usage.py --status          # Just show current status
    python example_pairing_usage.py --control-point   # Test control point commands
        """
    )
    
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=300, 
        help="Pairing timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--config", 
        default="configuration.json",
        help="Path to configuration file (default: configuration.json)"
    )
    parser.add_argument(
        "--no-qr", 
        action="store_true",
        help="Don't display QR code and setup information"
    )
    parser.add_argument(
        "--duration", 
        type=int, 
        default=600,
        help="How long to keep pairing mode active in seconds (default: 600)"
    )
    parser.add_argument(
        "--control-point", 
        action="store_true",
        help="Test control point pairing commands"
    )
    parser.add_argument(
        "--status", 
        action="store_true",
        help="Just show current pairing status"
    )
    
    args = parser.parse_args()
    
    print("🔧 HomeKit Re-Pairing Script for Apple HomeKey Reader")
    print("=" * 60)
    
    try:
        # Load configuration
        config = load_configuration(args.config)
        print(f"✅ Loaded configuration from {args.config}")
        
        # Set up components
        print("🔌 Setting up components...")
        nfc_device, service, driver, accessory = setup_components(config)
        print("✅ Components initialized successfully")
        
        # Handle different modes
        if args.status:
            # For status, we don't need to start the full HAP driver
            print("\n📊 Checking pairing status...")
            show_pairing_status(service)
            return 0
        
        if args.control_point:
            test_control_point_commands(service)
            return 0
        
        # Start HAP driver for pairing
        print("\n🚀 Starting HAP driver...")
        
        # Use a result container to capture the pairing result
        result_container = {'success': False, 'completed': False}
        
        def run_pairing():
            """Run pairing logic in separate thread"""
            try:
                # Give the HAP driver a moment to start up
                import time
                time.sleep(3)
                
                # Main pairing operation
                show_qr = not args.no_qr
                result_container['success'] = pair_new_device(service, driver, args.timeout, show_qr, args.duration)
                result_container['completed'] = True
                
                # Stop the driver after pairing attempt
                driver.stop()
                
            except Exception as e:
                log.error(f"Pairing thread failed: {e}")
                result_container['completed'] = True
                driver.stop()
        
        # Start pairing in background thread
        pairing_thread = threading.Thread(target=run_pairing, daemon=True)
        pairing_thread.start()
        
        try:
            # Start the HAP driver (this will block until stopped)
            driver.start()
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user")
            driver.stop()
            result_container['completed'] = True
        except Exception as e:
            log.error(f"HAP driver error: {e}")
            driver.stop()
            result_container['completed'] = True
        
        # Wait for pairing thread to complete
        pairing_thread.join(timeout=10)
        
        return 0 if result_container.get('success', False) else 1
            
    except Exception as e:
        log.error(f"Script failed: {e}")
        print(f"\n❌ Script failed: {e}")
        return 1

if __name__ == "__main__":
    import time  # Import here to avoid unused import warning
    sys.exit(main())
