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
    """Show setup code and QR information from current HAP state"""
    import json
    import os
    
    hap_state_file = "hap.state"
    
    if not os.path.exists(hap_state_file):
        print("❌ HAP state file not found")
        return False
    
    try:
        with open(hap_state_file, 'r') as f:
            state = json.load(f)
        
        setup_id = state.get('setup_id')
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
            return True
        else:
            print("⚠️ No setup code found in HAP state")
            return False
            
    except Exception as e:
        print(f"❌ Failed to read setup info: {e}")
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