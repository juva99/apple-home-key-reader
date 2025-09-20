#!/usr/bin/env python3
"""
Apple Home Key Reader - Add New Device Tool

This tool helps you add new iOS devices to HomeKit without affecting existing paired devices.
Unlike resetting the entire HomeKit setup, this preserves all existing pairings and just 
displays the information needed to add a new device.

Usage:
    python3 add_new_device.py
    python3 add_new_device.py --config configuration.json
    python3 add_new_device.py --show-qr  # Show QR code for easy scanning
    python3 add_new_device.py --restart-service  # Restart service after showing info
"""

import os
import sys
import json
import argparse
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if HAP-python is available"""
    try:
        import pyhap
        return True
    except ImportError:
        return False

def check_qr_dependencies():
    """Check if qrcode package is available"""
    try:
        import qrcode
        return True
    except ImportError:
        return False

class NewDeviceManager:
    def __init__(self, config_path="configuration.json"):
        self.config_path = config_path
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if not os.path.exists(self.config_path):
                print(f"❌ Configuration file not found: {self.config_path}")
                print("Make sure you're running this from the correct directory")
                sys.exit(1)
            
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            
            print(f"✅ Configuration loaded from {self.config_path}")
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            sys.exit(1)
    
    def validate_setup_code(self, setup_code):
        """Validate HomeKit setup code format"""
        if not setup_code:
            return False
        
        # Convert to string and clean up
        setup_code_str = str(setup_code).strip()
        
        # Remove any dashes or spaces
        clean_code = setup_code_str.replace('-', '').replace(' ', '')
        
        # Must be exactly 8 digits
        if len(clean_code) != 8:
            return False
        
        # Must be all numeric
        if not clean_code.isdigit():
            return False
        
        # Additional validation - common invalid codes
        invalid_codes = ['00000000', '11111111', '12345678', '87654321']
        if clean_code in invalid_codes:
            return False
        
        return True
    
    def format_setup_code(self, setup_code):
        """Format setup code in XXX-XX-XXX format"""
        if not setup_code:
            return None
        
        clean_code = str(setup_code).replace('-', '').replace(' ', '')
        if len(clean_code) == 8 and clean_code.isdigit():
            return f"{clean_code[:3]}-{clean_code[3:5]}-{clean_code[5:]}"
        return None
    
    def get_current_setup_info(self):
        """Get current HomeKit setup information"""
        if not check_dependencies():
            print("⚠️  HAP-python not available. Install with: pip install HAP-python")
            return None, None
        
        try:
            from pyhap.accessory_driver import AccessoryDriver
            
            # Create a temporary driver to read current state
            temp_driver = AccessoryDriver(
                port=self.config["hap"]["port"],
                persist_file=self.config["hap"]["persist"]
            )
            
            # Try different attribute names for setup code
            setup_code = None
            setup_uri = None
            
            if hasattr(temp_driver.state, 'setup_code'):
                setup_code = temp_driver.state.setup_code
            elif hasattr(temp_driver.state, 'setup_id'):
                setup_code = temp_driver.state.setup_id
            elif hasattr(temp_driver.state, 'pincode'):
                setup_code = temp_driver.state.pincode
            
            # Try to get setup URI
            if hasattr(temp_driver.state, 'setup_uri'):
                setup_uri = temp_driver.state.setup_uri
            elif hasattr(temp_driver.state, 'uri'):
                setup_uri = temp_driver.state.uri
            
            # Validate the setup code
            if setup_code and not self.validate_setup_code(setup_code):
                print(f"⚠️  Warning: Setup code '{setup_code}' appears invalid")
                print("   HomeKit setup codes must be 8 numeric digits")
                setup_code = None
            
            return setup_code, setup_uri
            
        except Exception as e:
            print(f"⚠️  Could not read current setup info: {e}")
            return None, None
    
    def show_setup_qr(self, setup_uri=None):
        """Show QR code for HomeKit setup"""
        if not setup_uri:
            print("📱 QR Code: Not available (no setup URI)")
            return
        
        if not check_qr_dependencies():
            print("📱 QR Code: Install 'qrcode' package to display QR codes")
            print("   Run: pip install qrcode")
            print(f"   Setup URI: {setup_uri}")
            return
        
        try:
            import qrcode
            
            # Create QR code with ASCII output (no PIL required)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(setup_uri)
            qr.make(fit=True)
            
            print("\n📱 HomeKit Setup QR Code:")
            print("=" * 30)
            qr.print_ascii(invert=True)
            print("=" * 30)
            print("Scan this QR code with the Home app on your iOS device")
            
        except Exception as e:
            print(f"📱 QR Code error: {e}")
            print(f"   Setup URI: {setup_uri}")
    
    def show_device_info(self, show_qr=False):
        """Display information for adding a new device"""
        print("\n🏠 Apple Home Key Reader - Add New Device")
        print("=" * 45)
        print("\nThis tool helps you add a new iOS device to HomeKit while")
        print("preserving all existing paired devices and their access.")
        
        # Check if state file exists
        persist_file = self.config["hap"]["persist"]
        if not os.path.exists(persist_file):
            print(f"\n❌ HomeKit state file not found: {persist_file}")
            print("   Run the main application first to create initial pairing")
            print("   Command: python3 main.py")
            return
        
        print(f"\n✅ HomeKit state file found: {persist_file}")
        print("   Existing device pairings will be preserved")
        
        # Get current setup information
        setup_code, setup_uri = self.get_current_setup_info()
        
        print("\n📋 Setup Information for New Device:")
        print("=" * 40)
        
        if setup_code:
            formatted_code = self.format_setup_code(setup_code)
            if formatted_code:
                print(f"🔢 Setup Code: {formatted_code}")
            else:
                print(f"🔢 Setup Code: {setup_code}")
        else:
            print("🔢 Setup Code: Not available")
            print("   Start the main service to generate a setup code")
        
        print(f"🌐 Network Port: {self.config['hap']['port']}")
        print(f"📱 Device Name: {self.config['hap'].get('name', 'NFC Lock')}")
        print(f"🏷️  Category: {self.config['hap'].get('category', 'Door Lock')}")
        
        # Show QR code if requested and available
        if show_qr and setup_uri:
            self.show_setup_qr(setup_uri)
        elif show_qr:
            print("\n📱 QR Code: Not available")
            print("   Start the main service to generate setup URI")
        
        print("\n📱 Adding Your New Device:")
        print("=" * 30)
        print("1. Make sure the main service is running:")
        print("   python3 main.py")
        print()
        print("2. On your NEW iOS device:")
        print("   • Open the Home app")
        print("   • Tap '+' in the top right")
        print("   • Select 'Add Accessory'")
        print("   • Tap 'More Options...'")
        print()
        print("3. Choose one method:")
        if setup_code:
            formatted_code = self.format_setup_code(setup_code)
            print(f"   Method A: Look for 'NFC Lock' in nearby accessories")
            print(f"   Method B: Tap 'Enter Code Manually' and enter: {formatted_code or setup_code}")
        else:
            print("   • Look for 'NFC Lock' in nearby accessories")
            print("   • If not found, check console output for setup code")
        
        if show_qr and setup_uri:
            print("   Method C: Scan the QR code shown above")
        
        print()
        print("4. Follow the setup wizard to complete pairing")
        
        print("\n✅ Important Notes:")
        print("=" * 20)
        print("• This process does NOT affect existing paired devices")
        print("• All current users keep their access permissions")
        print("• The new device will be added alongside existing ones")
        print("• No need to delete or reset the hap.state file")
        
        print("\n🔧 Troubleshooting:")
        print("=" * 18)
        print("• Ensure both devices are on the same WiFi network")
        print(f"• Check that port {self.config['hap']['port']} is not blocked by firewall")
        print("• If accessory doesn't appear, restart the main service")
        print("• If setup fails, check the main service console for errors")
        
        if not setup_code:
            print()
            print("⚠️  No setup code available:")
            print("   1. Make sure the main service is running")
            print("   2. Check console output for 'Setup code: XXX-XX-XXX'")
            print("   3. Use that code for manual entry in the Home app")
    
    def restart_service(self):
        """Restart the main service"""
        print("\n🔄 Restarting HomeKit service...")
        print("=" * 35)
        
        # This is a basic implementation - could be enhanced based on how the service is run
        print("To restart the service:")
        print("1. Stop the current main.py process (Ctrl+C)")
        print("2. Run: python3 main.py")
        print()
        print("If running as a system service, use appropriate service commands")
    
    def check_status(self):
        """Check current status and provide recommendations"""
        print("\n📊 System Status Check")
        print("=" * 25)
        
        # Check dependencies
        if check_dependencies():
            print("✅ HAP-python library available")
        else:
            print("❌ HAP-python library missing - install with: pip install HAP-python")
        
        if check_qr_dependencies():
            print("✅ QR code generation available")
        else:
            print("⚠️  QR code library missing - install with: pip install qrcode")
        
        # Check configuration
        print(f"✅ Configuration file: {self.config_path}")
        
        # Check state file
        persist_file = self.config["hap"]["persist"]
        if os.path.exists(persist_file):
            print(f"✅ HomeKit state file: {persist_file}")
            
            # Check file size to see if it has pairings
            file_size = os.path.getsize(persist_file)
            if file_size > 100:  # Rough estimate
                print("   Contains existing pairings - safe to add new devices")
            else:
                print("   File exists but may be empty - run main service first")
        else:
            print(f"❌ HomeKit state file missing: {persist_file}")
            print("   Run main service first: python3 main.py")
        
        # Network check
        print(f"🌐 Configured port: {self.config['hap']['port']}")
        
        print("\n💡 Recommendations:")
        if not os.path.exists(persist_file):
            print("• Run the main service first to establish initial pairing")
        elif check_dependencies() and check_qr_dependencies():
            print("• System ready - you can add new devices safely")
        else:
            print("• Install missing dependencies for full functionality")

def main():
    parser = argparse.ArgumentParser(
        description="Add new iOS devices to Apple Home Key Reader without affecting existing pairings"
    )
    parser.add_argument(
        "--config", 
        default="configuration.json",
        help="Path to configuration file (default: configuration.json)"
    )
    parser.add_argument(
        "--show-qr", 
        action="store_true",
        help="Display QR code for easy setup"
    )
    parser.add_argument(
        "--restart-service", 
        action="store_true",
        help="Show instructions to restart the main service"
    )
    parser.add_argument(
        "--status", 
        action="store_true",
        help="Check system status and dependencies"
    )
    
    args = parser.parse_args()
    
    try:
        manager = NewDeviceManager(args.config)
        
        if args.status:
            manager.check_status()
        else:
            manager.show_device_info(show_qr=args.show_qr)
        
        if args.restart_service:
            manager.restart_service()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
