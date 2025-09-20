#!/usr/bin/env python3
"""
HomeKit Reconnection Script for Apple Home Key Reader

This script helps users reconnect their Apple Home Key Reader to HomeKit
after the initial setup has been completed. It provides options to:

1. Reset HomeKit pairing and start fresh
2. Display current pairing information  
3. Restart the HomeKit service with existing configuration
4. Check configuration and connection status

Usage:
    python3 reconnect_homekit_standalone.py [options]

Options:
    --reset-pairing    Reset all HomeKit pairings and start fresh
    --check-status     Display current pairing and configuration status
    --restart-service  Restart the HomeKit service with current config
    --show-qr         Show the HomeKit setup QR code
    --help            Show this help message
"""

import argparse
import os
import sys
import time
import json

def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    
    try:
        import importlib.util
        spec = importlib.util.find_spec("pyhap")
        if spec is None:
            missing.append("HAP-python")
    except ImportError:
        missing.append("HAP-python")
    
    if missing:
        print("❌ Missing required dependencies:")
        for dep in missing:
            print(f"   • {dep}")
        print("\n📦 Install dependencies with:")
        print("   pip install -r requirements.txt")
        print("\n💡 Make sure you're in the correct project directory and have activated your virtual environment if using one.")
        return False
    
    return True

def load_config_safe(config_path="configuration.json"):
    """Safely load configuration file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        print("💡 Make sure you're running this script from the project directory.")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in configuration file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return None

class SimpleHomeKitReconnector:
    def __init__(self, config_path="configuration.json"):
        self.config_path = config_path
        self.config = load_config_safe(config_path)
        
        if not self.config:
            sys.exit(1)
    
    def check_status(self):
        """Check and display current HomeKit and configuration status"""
        print("\n🔍 Checking Apple Home Key Reader Status...")
        print("=" * 50)
        
        # Check configuration files
        hap_state_file = self.config["hap"]["persist"]
        homekey_file = self.config["homekey"]["persist"]
        
        print(f"📁 Configuration File: {self.config_path}")
        print(f"   ✅ Exists: {os.path.exists(self.config_path)}")
        
        print(f"\n🏠 HomeKit State File: {hap_state_file}")
        hap_exists = os.path.exists(hap_state_file)
        print(f"   {'✅' if hap_exists else '❌'} Exists: {hap_exists}")
        
        print(f"\n🔑 Home Key Data File: {homekey_file}")
        homekey_exists = os.path.exists(homekey_file)
        print(f"   {'✅' if homekey_exists else '❌'} Exists: {homekey_exists}")
        
        # Analyze HomeKit state file
        if hap_exists:
            try:
                stat = os.stat(hap_state_file)
                print(f"   📊 File size: {stat.st_size} bytes")
                print(f"   🕐 Last modified: {time.ctime(stat.st_mtime)}")
                
                # Simple check - if file is very small, likely not paired
                if stat.st_size < 100:
                    print("   ⚠️  File seems small - may not contain pairing data")
                else:
                    print("   ✅ File contains data (likely paired)")
                    
            except Exception as e:
                print(f"   ❌ Error reading file info: {e}")
        
        # Analyze Home Key data file
        if homekey_exists:
            try:
                with open(homekey_file, 'r') as f:
                    data = json.load(f)
                
                reader_key = data.get("reader_private_key", "00" * 32)
                issuers = data.get("issuers", {})
                
                print("\n🔐 Home Key Configuration:")
                configured = reader_key != "00" * 32
                print(f"   Reader Key Set: {'✅ Yes' if configured else '❌ No'}")
                print(f"   Issuers (iCloud accounts): {len(issuers)}")
                
                if issuers:
                    total_endpoints = 0
                    print("   👤 Configured issuers:")
                    for issuer_id, issuer in issuers.items():
                        endpoints = len(issuer.get("endpoints", []))
                        total_endpoints += endpoints
                        print(f"      • Issuer ID: {issuer_id[:16]}...")
                        print(f"        Endpoints: {endpoints}")
                    print(f"   📱 Total Endpoints (devices): {total_endpoints}")
                        
            except Exception as e:
                print(f"   ❌ Error reading Home Key data: {e}")
        
        # Check NFC configuration
        print("\n📡 NFC Configuration:")
        print(f"   Device Path: {self.config['nfc']['path']}")
        print(f"   Broadcast Enabled: {self.config['nfc']['broadcast']}")
        
        print("\n🌐 HomeKit Network Configuration:")
        print(f"   Port: {self.config['hap']['port']}")
        print(f"   Default State: {self.config['hap']['default']}")
        
        # Provide recommendations
        print("\n💡 Recommendations:")
        if not hap_exists:
            print("   • No HomeKit pairing file found - run initial setup")
        elif not homekey_exists:
            print("   • No Home Key data file found - complete HomeKit setup first")
        else:
            print("   • Configuration files present - try restarting the service")
    
    def reset_pairing(self):
        """Reset HomeKit pairing and start fresh"""
        print("\n🔄 Resetting HomeKit Pairing...")
        print("=" * 40)
        
        hap_state_file = self.config["hap"]["persist"]
        
        # Confirm with user
        response = input("⚠️  This will remove all HomeKit pairings. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            return
        
        # Backup existing state
        if os.path.exists(hap_state_file):
            backup_file = f"{hap_state_file}.backup.{int(time.time())}"
            try:
                if os.name == 'nt':  # Windows
                    os.system(f'copy "{hap_state_file}" "{backup_file}"')
                else:  # Unix-like
                    os.system(f'cp "{hap_state_file}" "{backup_file}"')
                
                os.remove(hap_state_file)
                print(f"✅ Backed up existing state to: {backup_file}")
                print("✅ HomeKit pairing file removed")
            except Exception as e:
                print(f"❌ Error resetting pairing: {e}")
                return
        else:
            print("✅ No existing pairing file to remove")
        
        print("✅ HomeKit pairing reset complete!")
        print("\n📱 To reconnect:")
        print("1. Run the main application: python3 main.py")
        print("2. Look for the setup code in the console output")
        print("3. Open the Home app on your iOS device")
        print("4. Tap the '+' button and select 'Add Accessory'")
        print("5. Enter the 8-digit setup code manually")
        print("6. Follow the on-screen instructions")
    
    def show_info(self):
        """Show setup information and try to get current PIN if possible"""
        print("\n📋 HomeKit Setup Information:")
        print("=" * 35)
        
        # Try to get current setup PIN if dependencies are available
        current_pin = None
        try:
            if check_dependencies():
                # Try to get the current setup code
                from pyhap.accessory_driver import AccessoryDriver
                temp_driver = AccessoryDriver(
                    port=self.config["hap"]["port"], 
                    persist_file=self.config["hap"]["persist"]
                )
                
                # Try different attributes for setup code
                if hasattr(temp_driver.state, 'setup_code'):
                    current_pin = temp_driver.state.setup_code
                elif hasattr(temp_driver.state, 'setup_id'):
                    current_pin = temp_driver.state.setup_id
                elif hasattr(temp_driver.state, 'pincode'):
                    current_pin = temp_driver.state.pincode
        except Exception:
            pass  # Ignore errors when trying to get PIN
        
        if current_pin:
            print(f"� Current Setup PIN: {current_pin}")
            print("\n📱 Quick Setup:")
            print("1. Open the Home app on your iOS device")
            print("2. Tap '+' → 'Add Accessory' → 'More Options'")
            print("3. Look for 'NFC Lock' in nearby accessories")
            print(f"4. If not found, tap 'Enter Code Manually' and enter: {current_pin}")
            print("5. Follow the setup instructions")
        else:
            print("🔢 Setup PIN: Check console output when running 'python3 main.py'")
            print("🌐 Network Port:", self.config['hap']['port'])
            print("📁 State File:", self.config['hap']['persist'])
            
            print("\n📱 Setup Steps:")
            print("1. Ensure the main application is running: python3 main.py")
            print("2. Look for a message like 'Setup code: XXX-XX-XXX' in the output")
            print("3. Open the Home app on your iOS device")
            print("4. Tap '+' → 'Add Accessory' → 'More Options'")
            print("5. Look for 'NFC Lock' in the nearby accessories")
            print("6. If not found, tap 'Enter Code Manually' and enter the setup code")
            print("7. Follow the setup wizard")
        
        print("\n🔧 Troubleshooting:")
        print("• Make sure your iOS device and this computer are on the same network")
        print("• Check that no firewall is blocking port", self.config['hap']['port'])
        print("• If the accessory doesn't appear, try restarting the application")
        print("• If PIN is not shown above, ensure dependencies are installed")
    
    def check_service(self):
        """Check if the service can start"""
        print("\n🔧 Service Check...")
        print("=" * 25)
        
        try:
            # Check if dependencies are available
            if not check_dependencies():
                return
            
            # Try to import and check basic functionality
            from main import load_configuration, configure_logging
            
            config = load_configuration(self.config_path)
            configure_logging(config["logging"])
            
            print("✅ Configuration loads successfully")
            print("✅ Logging configured")
            
            # Check Home Key configuration
            homekey_file = config["homekey"]["persist"]
            if os.path.exists(homekey_file):
                with open(homekey_file, 'r') as f:
                    data = json.load(f)
                reader_key = data.get("reader_private_key", "00" * 32)
                
                if reader_key != "00" * 32:
                    print("✅ Home Key reader is configured")
                else:
                    print("❌ Home Key reader not configured - complete setup first")
                    return
            else:
                print("❌ Home Key data file missing - complete setup first")
                return
            
            print("\n✅ Service appears ready to start")
            print("💡 Run 'python3 main.py' to start the full service")
            
        except Exception as e:
            print(f"❌ Service check failed: {e}")
            print("💡 Make sure all dependencies are installed")


def main():
    parser = argparse.ArgumentParser(
        description="HomeKit Reconnection Tool for Apple Home Key Reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--reset-pairing", 
        action="store_true",
        help="Reset all HomeKit pairings and start fresh"
    )
    
    parser.add_argument(
        "--check-status", 
        action="store_true",
        help="Display current pairing and configuration status"
    )
    
    parser.add_argument(
        "--show-info", 
        action="store_true",
        help="Show setup information and instructions"
    )
    
    parser.add_argument(
        "--check-service", 
        action="store_true",
        help="Check if the service is ready to start"
    )
    
    parser.add_argument(
        "--config", 
        default="configuration.json",
        help="Path to configuration file (default: configuration.json)"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help and status
    if not any([args.reset_pairing, args.check_status, args.show_info, args.check_service]):
        parser.print_help()
        print("\n" + "="*50)
        
        if not check_dependencies():
            return
        
        reconnector = SimpleHomeKitReconnector(args.config)
        reconnector.check_status()
        return
    
    # Check dependencies for operations that need them
    if args.check_service:
        if not check_dependencies():
            return
    
    try:
        reconnector = SimpleHomeKitReconnector(args.config)
        
        print("🍎 Apple Home Key Reader - HomeKit Reconnection Tool")
        print("=" * 55)
        
        if args.check_status:
            reconnector.check_status()
        
        if args.reset_pairing:
            reconnector.reset_pairing()
        
        if args.show_info:
            reconnector.show_info()
            
        if args.check_service:
            reconnector.check_service()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
