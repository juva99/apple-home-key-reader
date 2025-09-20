#!/usr/bin/env python3
"""
Enhanced HomeKit Pairing Mode Script

This script enables pairing mode and displays the setup code/QR information
for adding new HomeKit controllers to your Apple HomeKey Reader.

Usage:
    python pairing_helper.py [duration]

Arguments:
    duration    How long to keep pairing mode active in seconds (default: 600)
"""

import sys
import json
import os
import time
import signal
import threading

def get_hap_setup_info():
    """Get HomeKit setup information by reading HAP configuration"""
    try:
        # Load configuration
        with open("configuration.json", 'r') as f:
            config = json.load(f)
        
        # The setup code is typically derived from the device ID and other factors
        # For pyhap, it's usually generated when the driver starts in unpaired mode
        
        # Read current HAP state
        hap_state_file = config["hap"]["persist"]
        
        if os.path.exists(hap_state_file):
            with open(hap_state_file, 'r') as f:
                state = json.load(f)
            
            # Check if setup_id exists (added when in pairing mode)
            setup_id = state.get('setup_id')
            if setup_id:
                return format_setup_info(setup_id)
            
            # If no setup_id, we need to generate it
            # This typically happens when HAP driver initializes
            print("💡 Setup code will be generated when pairing mode is active")
            
        return None
        
    except Exception as e:
        print(f"⚠️ Could not get setup info: {e}")
        return None

def format_setup_info(setup_id):
    """Format setup code and QR information"""
    if not setup_id or len(setup_id) < 8:
        return None
    
    formatted_code = f"{setup_id[:3]}-{setup_id[3:5]}-{setup_id[5:]}"
    qr_uri = f"X-HM://{setup_id}"
    
    return {
        'setup_id': setup_id,
        'formatted_code': formatted_code,
        'qr_uri': qr_uri
    }

def display_setup_info(setup_info):
    """Display setup information in a user-friendly format"""
    if not setup_info:
        return False
    
    print("\n🔗 HomeKit Setup Information")
    print("=" * 50)
    print(f"📋 Setup Code: {setup_info['formatted_code']}")
    print(f"🔗 QR URI: {setup_info['qr_uri']}")
    print("\n📱 To pair with HomeKit:")
    print("1. Open the Home app on your iOS device")
    print("2. Tap '+' to add an accessory")
    print("3. Choose 'Add Accessory'")
    print(f"4. Enter setup code: {setup_info['formatted_code']}")
    print("   OR generate and scan a QR code from the URI above")
    
    # Try to display QR code if qrcode is available
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(setup_info['qr_uri'])
        qr.make(fit=True)
        print("\n📋 QR Code:")
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"\n📋 QR Code URI: {setup_info['qr_uri']}")
        print("   💡 Install 'qrcode' package to display QR code: pip install qrcode[pil]")
    except Exception as e:
        print(f"📋 QR Code URI: {setup_info['qr_uri']}")
    
    print("=" * 50)
    return True

def enable_pairing_mode(duration_seconds=600):
    """Enable pairing mode by modifying HAP state and monitoring setup info"""
    hap_state_file = "hap.state"
    
    if not os.path.exists(hap_state_file):
        print("❌ HAP state file not found. Make sure your HomeKey service has been set up.")
        return False
    
    try:
        # Read current HAP state
        with open(hap_state_file, 'r') as f:
            state = json.load(f)
        
        # Check current pairing state
        original_paired = state.get('paired', False)
        has_clients = bool(state.get('paired_clients', {}))
        
        if not original_paired and not has_clients:
            print("ℹ️ Device is already in pairing mode")
            setup_info = get_hap_setup_info()
            if setup_info:
                display_setup_info(setup_info)
            return True
        
        print(f"🔗 Enabling pairing mode for {duration_seconds} seconds...")
        
        # Backup original state
        backup_state = state.copy()
        
        # Enable pairing mode
        state['paired'] = False
        # Note: We keep paired_clients so existing controllers still work
        
        # Write modified state
        with open(hap_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        print(f"✅ Pairing mode enabled!")
        print("📱 New HomeKit controllers can now pair with your device")
        print("🔄 Existing controllers remain functional")
        print(f"⏰ Will automatically disable after {duration_seconds} seconds")
        
        # Monitor for setup info updates
        setup_displayed = False
        start_time = time.time()
        
        # Set up signal handler for graceful shutdown
        shutdown_event = threading.Event()
        
        def signal_handler(signum, frame):
            print("\n🛑 Disabling pairing mode...")
            shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Monitor for setup info and handle timeout
        while not shutdown_event.is_set():
            # Check for setup info every few seconds
            if not setup_displayed:
                setup_info = get_hap_setup_info()
                if setup_info:
                    display_setup_info(setup_info)
                    setup_displayed = True
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= duration_seconds:
                print(f"\n⏰ Timeout reached ({duration_seconds} seconds)")
                break
            
            # Wait before next check
            if shutdown_event.wait(5):  # Check every 5 seconds
                break
        
        # Restore original state
        with open(hap_state_file, 'w') as f:
            json.dump(backup_state, f, indent=2)
        
        print("🔄 Pairing mode disabled - restored original state")
        
        if not setup_displayed:
            print("\n💡 Note: Setup code is generated by the HAP driver when it restarts")
            print("   You may need to restart your HomeKey service to see the setup code")
            print("   Or check your service logs for the setup information")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to enable pairing mode: {e}")
        # Try to restore state if something went wrong
        try:
            if 'backup_state' in locals():
                with open(hap_state_file, 'w') as f:
                    json.dump(backup_state, f, indent=2)
                print("🔄 Restored original state after error")
        except:
            pass
        return False

def main():
    """Main script entry point"""
    print("🔧 HomeKit Pairing Helper")
    print("=" * 40)
    
    # Parse arguments
    duration = 600  # Default 10 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid duration. Please provide a number of seconds.")
            print("Usage: python pairing_helper.py [duration_seconds]")
            sys.exit(1)
    
    # Check if setup info is already available
    print("🔍 Checking current setup information...")
    setup_info = get_hap_setup_info()
    if setup_info:
        print("📋 Found existing setup information:")
        display_setup_info(setup_info)
        
        response = input("\n❓ Setup info is available. Enable pairing mode anyway? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("ℹ️ Use the setup code above to pair new devices")
            return 0
    
    # Enable pairing mode
    success = enable_pairing_mode(duration)
    
    if success:
        print("\n✅ Pairing session completed")
    else:
        print("\n❌ Pairing session failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())