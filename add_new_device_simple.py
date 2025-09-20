#!/usr/bin/env python3
"""
Apple Home Key Reader - Add New Device (Simple)

Simple tool to show setup information for adding new iOS devices to HomeKit.
This version has minimal dependencies and works even without HAP-python installed.

Usage:
    python3 add_new_device_simple.py
    python3 add_new_device_simple.py --config configuration.json
"""

import os
import sys
import json
import argparse

class SimpleNewDeviceManager:
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
    
    def check_dependencies(self):
        """Check if HAP-python is available"""
        try:
            import pyhap
            return True
        except ImportError:
            return False
    
    def get_setup_info_if_available(self):
        """Try to get setup info if dependencies are available"""
        if not self.check_dependencies():
            return None
        
        try:
            from pyhap.accessory_driver import AccessoryDriver
            
            temp_driver = AccessoryDriver(
                port=self.config["hap"]["port"],
                persist_file=self.config["hap"]["persist"]
            )
            
            # Try different attribute names
            setup_code = None
            if hasattr(temp_driver.state, 'setup_code'):
                setup_code = temp_driver.state.setup_code
            elif hasattr(temp_driver.state, 'setup_id'):
                setup_code = temp_driver.state.setup_id
            elif hasattr(temp_driver.state, 'pincode'):
                setup_code = temp_driver.state.pincode
            
            # Validate setup code
            if setup_code:
                clean_code = str(setup_code).replace('-', '').replace(' ', '')
                if len(clean_code) == 8 and clean_code.isdigit():
                    return f"{clean_code[:3]}-{clean_code[3:5]}-{clean_code[5:]}"
            
            return setup_code
            
        except Exception:
            return None
    
    def show_add_device_info(self):
        """Show simple information for adding a new device"""
        print("\n🏠 Add New Device to Apple Home Key Reader")
        print("=" * 45)
        
        # Check state file
        persist_file = self.config["hap"]["persist"]
        if os.path.exists(persist_file):
            print("✅ Existing HomeKit pairings will be preserved")
        else:
            print("⚠️  No existing pairings found")
            print("   Run the main application first: python3 main.py")
        
        print(f"\n📋 Device Information:")
        print(f"🏷️  Name: {self.config['hap'].get('name', 'NFC Lock')}")
        print(f"🌐 Port: {self.config['hap']['port']}")
        print(f"📁 State File: {self.config['hap']['persist']}")
        
        # Try to get current setup code
        current_setup_code = self.get_setup_info_if_available()
        
        print(f"\n🔢 Setup Code:")
        if current_setup_code:
            print(f"   {current_setup_code}")
        else:
            if self.check_dependencies():
                print("   Not available - start the main service")
            else:
                print("   Install HAP-python to read current code")
                print("   Or check main service console output")
        
        print(f"\n📱 How to Add Your New Device:")
        print("=" * 35)
        
        print("1. Ensure the main service is running:")
        print("   python3 main.py")
        print()
        
        print("2. On your NEW iOS device, open the Home app:")
        print("   • Tap '+' (top right)")
        print("   • Select 'Add Accessory'")
        print("   • Tap 'More Options...'")
        print()
        
        print("3. Find the accessory:")
        print("   • Look for 'NFC Lock' in nearby devices")
        print("   • OR tap 'Enter Code Manually'")
        
        if current_setup_code:
            print(f"   • Enter setup code: {current_setup_code}")
        else:
            print("   • Check main service console for setup code")
            print("     (Look for 'Setup code: XXX-XX-XXX')")
        
        print()
        print("4. Complete the setup wizard")
        
        print(f"\n✅ Key Points:")
        print("• This does NOT delete existing pairings")
        print("• All current devices keep their access")
        print("• No need to reset or delete hap.state file")
        print("• Both devices must be on the same WiFi network")
        
        if not current_setup_code and not self.check_dependencies():
            print(f"\n💡 For more features, install HAP-python:")
            print("   pip install HAP-python")
        
        print(f"\n🔧 If you have issues:")
        print(f"• Restart the main service")
        print(f"• Check firewall settings for port {self.config['hap']['port']}")
        print(f"• Ensure both devices are on same network")

def main():
    parser = argparse.ArgumentParser(
        description="Simple tool to add new iOS devices to Apple Home Key Reader"
    )
    parser.add_argument(
        "--config", 
        default="configuration.json",
        help="Path to configuration file (default: configuration.json)"
    )
    
    args = parser.parse_args()
    
    try:
        manager = SimpleNewDeviceManager(args.config)
        manager.show_add_device_info()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
