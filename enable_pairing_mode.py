#!/usr/bin/env python3
"""
Simple HomeKit Pairing Mode Script

This script simply enables pairing mode on your existing HAP setup
to allow new HomeKit devices to pair without disrupting the current service.

Usage:
    python enable_pairing_mode.py [duration]

Arguments:
    duration    How long to keep pairing mode active in seconds (default: 600)
"""

import sys
import signal
import threading
import time

def enable_pairing_mode(duration_seconds=600):
    """Enable pairing mode by temporarily modifying the HAP state"""
    import json
    import os
    
    hap_state_file = "hap.state"
    
    if not os.path.exists(hap_state_file):
        print("❌ HAP state file not found. Run the main service first.")
        return False
    
    try:
        # Read current HAP state
        with open(hap_state_file, 'r') as f:
            state = json.load(f)
        
        # Check if already paired
        if not state.get('paired', False):
            print("ℹ️ Device is already in pairing mode")
            return True
        
        print(f"🔗 Enabling pairing mode for {duration_seconds} seconds...")
        print("📱 You can now add this accessory to new HomeKit controllers")
        print("💡 Open the Home app and scan the QR code or enter the setup code")
        
        # Backup original state
        original_paired = state['paired']
        
        # Temporarily set to unpaired to allow new pairings
        state['paired'] = False
        
        # Write modified state
        with open(hap_state_file, 'w') as f:
            json.dump(state, f)
        
        print(f"✅ Pairing mode enabled!")
        print(f"⏰ Will automatically disable after {duration_seconds} seconds")
        
        # Now try to get setup information after enabling pairing mode
        print("\n🔍 Getting setup information...")
        try:
            # Re-read the modified state to get setup info
            with open(hap_state_file, 'r') as f:
                updated_state = json.load(f)
            
            setup_id = updated_state.get('setup_id')
            if setup_id:
                formatted_code = f"{setup_id[:3]}-{setup_id[3:5]}-{setup_id[5:]}"
                qr_uri = f"X-HM://{setup_id}"
                
                print("\n🔗 HomeKit Setup Information")
                print("=" * 50)
                print(f"📋 Setup Code: {formatted_code}")
                print(f"🔗 QR URI: {qr_uri}")
                print("\n📱 To pair with HomeKit:")
                print("1. Open the Home app on your iOS device")
                print("2. Tap '+' to add an accessory")
                print("3. Choose 'Add Accessory'")
                print(f"4. Enter setup code: {formatted_code}")
                print("   OR scan a QR code generated from the URI above")
                print("=" * 50)
            else:
                print("📋 Setup code will be generated when HAP driver restarts")
                print("💡 You may need to restart your main service to see the setup code")
                
        except Exception as e:
            print(f"⚠️ Could not get setup info immediately: {e}")
            print("💡 The setup code will be available when your HAP service restarts")
        
        print("⚠️  Press Ctrl+C to disable immediately")
        
        # Set up signal handler for graceful shutdown
        shutdown_event = threading.Event()
        
        def signal_handler(signum, frame):
            print("\n🛑 Disabling pairing mode...")
            shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Wait for timeout or signal
        shutdown_event.wait(duration_seconds)
        
        # Restore original state
        state['paired'] = original_paired
        with open(hap_state_file, 'w') as f:
            json.dump(state, f)
        
        print("🔄 Pairing mode disabled - restored original state")
        return True
        
    except Exception as e:
        print(f"❌ Failed to enable pairing mode: {e}")
        # Try to restore state if something went wrong
        try:
            if 'original_paired' in locals():
                state['paired'] = original_paired
                with open(hap_state_file, 'w') as f:
                    json.dump(state, f)
                print("🔄 Restored original state after error")
        except:
            pass
        return False

def show_current_setup_info():
    """Show setup code and QR information by initializing HAP components"""
    import json
    import os
    
    try:
        # Load configuration to get HAP settings
        with open("configuration.json", 'r') as f:
            config = json.load(f)
        
        # Initialize HAP driver to get setup information
        from pyhap.accessory_driver import AccessoryDriver
        from accessory import Lock
        from service import Service
        from repository import Repository
        from util.bfclf import BroadcastFrameContactlessFrontend
        
        # Create minimal components needed for setup info
        repository = Repository(config["homekey"]["persist"])
        nfc_device = BroadcastFrameContactlessFrontend(
            path=config.get("nfc", {}).get("path", None) or 
                 f"tty:{config.get('nfc', {}).get('port')}:{config.get('nfc', {}).get('driver')}",
            broadcast_enabled=False,  # Don't need broadcast for setup info
        )
        service = Service(
            clf=nfc_device,
            repository=repository,
            express=config.get("homekey", {}).get("express", True),
            finish=config.get("homekey", {}).get("finish", "silver"),
            flow=config.get("homekey", {}).get("flow", "fast"),
            throttle_polling=0.15,
            lock_timeout=10,
        )
        
        # Create HAP driver (but don't start it)
        driver = AccessoryDriver(
            port=config["hap"]["port"], 
            persist_file=config["hap"]["persist"]
        )
        
        accessory = Lock(
            driver,
            "NFC Lock",
            service=service,
            lock_state_at_startup=1,
            gpio_pin=config.get("hap", {}).get("gpio", {}).get("pin", None),
        )
        
        service.set_accessory_reference(accessory)
        driver.add_accessory(accessory=accessory)
        
        # Get setup information from the accessory
        pairing_info = accessory.get_pairing_info()
        
        if pairing_info:
            print("\n🔗 HomeKit Setup Information")
            print("=" * 50)
            print(f"📋 Setup Code: {pairing_info['formatted_setup_code']}")
            print(f"🔗 QR URI: {pairing_info['qr_uri']}")
            print("\n📱 To pair with HomeKit:")
            print("1. Open the Home app on your iOS device")
            print("2. Tap '+' to add an accessory")
            print("3. Choose 'Add Accessory'")
            print(f"4. Enter setup code: {pairing_info['formatted_setup_code']}")
            print("   OR scan a QR code generated from the URI above")
            
            # Try to show QR code if possible
            try:
                import qrcode
                qr = qrcode.QRCode(version=1, box_size=1, border=1)
                qr.add_data(pairing_info['qr_uri'])
                qr.make(fit=True)
                print("\n📋 QR Code:")
                qr.print_ascii(invert=True)
            except ImportError:
                print(f"\n📋 Generate QR code from: {pairing_info['qr_uri']}")
                print("   (Install 'qrcode' package to display QR code directly)")
            
            print("=" * 50)
            return True
        else:
            print("⚠️ Could not retrieve setup information")
            return False
            
    except Exception as e:
        print(f"❌ Failed to get setup info: {e}")
        
        # Fallback: try to read from HAP state file
        hap_state_file = "hap.state"
        if os.path.exists(hap_state_file):
            try:
                with open(hap_state_file, 'r') as f:
                    state = json.load(f)
                
                # Check if there's a setup_id in the state
                setup_id = state.get('setup_id')
                if setup_id:
                    formatted_code = f"{setup_id[:3]}-{setup_id[3:5]}-{setup_id[5:]}"
                    qr_uri = f"X-HM://{setup_id}"
                    
                    print(f"📋 Setup Code: {formatted_code}")
                    print(f"🔗 QR URI: {qr_uri}")
                    return True
                else:
                    print("⚠️ No setup code found in HAP state")
                    print("💡 This is normal if the device is already paired and not in pairing mode")
                    return False
                    
            except Exception as e2:
                print(f"❌ Failed to read HAP state: {e2}")
                return False
        else:
            print("❌ HAP state file not found")
            return False

def main():
    """Main script entry point"""
    print("🔧 HomeKit Pairing Mode Enabler")
    print("=" * 40)
    
    # Parse arguments
    duration = 600  # Default 10 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid duration. Please provide a number of seconds.")
            sys.exit(1)
    
    # Show current setup information
    print("📋 Current setup information:")
    show_current_setup_info()
    
    # Enable pairing mode
    success = enable_pairing_mode(duration)
    
    if success:
        print("\n✅ Pairing mode session completed successfully")
    else:
        print("\n❌ Pairing mode session failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())