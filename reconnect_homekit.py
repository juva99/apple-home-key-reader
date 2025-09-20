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
    python3 reconnect_homekit.py [options]

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

# Import project modules
from main import load_configuration, configure_logging, configure_hap_accessory, configure_nfc_device, configure_homekey_service
from repository import Repository
from pyhap.accessory_driver import AccessoryDriver

# Optional QR code support (without PIL dependency)
try:
    import qrcode
    # Test if we can create a QR code without PIL
    test_qr = qrcode.QRCode()
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


class HomeKitReconnector:
    def __init__(self, config_path="configuration.json"):
        self.config_path = config_path
        self.config = None
        self.logger = None
        self._load_config()
        
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            self.config = load_configuration(self.config_path)
            self.logger = configure_logging(self.config["logging"])
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
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
        print(f"   ✅ Exists: {os.path.exists(hap_state_file)}")
        
        print(f"\n🔑 Home Key Data File: {homekey_file}")
        print(f"   ✅ Exists: {os.path.exists(homekey_file)}")
        
        # Check HomeKit pairing status
        if os.path.exists(hap_state_file):
            try:
                # Create a temporary driver to check pairing status
                temp_driver = AccessoryDriver(
                    port=self.config["hap"]["port"], 
                    persist_file=hap_state_file
                )
                paired_clients = temp_driver.state.paired_clients
                print(f"\n👥 HomeKit Paired Clients: {len(paired_clients)}")
                
                if paired_clients:
                    print("   📱 Paired devices:")
                    for client_id, client_key in paired_clients.items():
                        print(f"      • Client ID: {client_id}")
                else:
                    print("   ❌ No devices currently paired")
                    
            except Exception as e:
                print(f"   ❌ Error reading HomeKit state: {e}")
        
        # Check Home Key configuration
        if os.path.exists(homekey_file):
            try:
                repository = Repository(homekey_file)
                reader_key = repository.get_reader_private_key()
                issuers = repository.get_all_issuers()
                endpoints = repository.get_all_endpoints()
                
                print("\n🔐 Home Key Configuration:")
                print(f"   Reader Key Set: {'✅ Yes' if reader_key != bytes.fromhex('00' * 32) else '❌ No'}")
                print(f"   Issuers (iCloud accounts): {len(issuers)}")
                print(f"   Endpoints (devices): {len(endpoints)}")
                
                if issuers:
                    print("   👤 Configured issuers:")
                    for issuer in issuers:
                        print(f"      • Issuer ID: {issuer.id.hex()}")
                        print(f"        Endpoints: {len(issuer.endpoints)}")
                        
            except Exception as e:
                print(f"   ❌ Error reading Home Key data: {e}")
        
        # Check NFC device
        print("\n📡 NFC Configuration:")
        print(f"   Device Path: {self.config['nfc']['path']}")
        print(f"   Broadcast Enabled: {self.config['nfc']['broadcast']}")
        
        print("\n🌐 HomeKit Network Configuration:")
        print(f"   Port: {self.config['hap']['port']}")
        print(f"   Default State: {self.config['hap']['default']}")
        
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
                os.rename(hap_state_file, backup_file)
                print(f"✅ Backed up existing state to: {backup_file}")
            except Exception as e:
                print(f"❌ Error backing up state file: {e}")
                return
        
        print("✅ HomeKit pairing reset complete!")
        print("\n📱 To reconnect:")
        print("1. Run the main application: python3 main.py")
        print("2. Open the Home app on your iOS device")
        print("3. Tap the '+' button and select 'Add Accessory'")
        print("4. Scan the QR code or enter the setup code manually")
        print("5. Follow the on-screen instructions")
        
        # Offer to show QR code
        show_qr = input("\n🔲 Show HomeKit setup QR code now? (y/N): ")
        if show_qr.lower() == 'y':
            self.show_setup_qr()
    
    def show_setup_qr(self):
        """Display the HomeKit setup QR code"""
        print("\n🔲 HomeKit Setup Information:")
        print("=" * 35)
        
        try:
            # Create a temporary driver to get the setup info
            temp_driver = AccessoryDriver(
                port=self.config["hap"]["port"], 
                persist_file=self.config["hap"]["persist"]
            )
            
            # Get setup code from different possible attributes
            setup_code = None
            setup_uri = None
            
            if hasattr(temp_driver.state, 'setup_code'):
                setup_code = temp_driver.state.setup_code
            elif hasattr(temp_driver.state, 'setup_id'):
                setup_code = temp_driver.state.setup_id
            elif hasattr(temp_driver.state, 'pincode'):
                setup_code = temp_driver.state.pincode
            
            # Construct setup URI if we have a setup code
            if setup_code:
                setup_uri = f"X-HM://{setup_code}"
            
            if setup_code:
                print(f"📍 HomeKit Setup PIN: {setup_code}")
                print("\n📱 How to use the Setup PIN:")
                print("1. Open the Home app on your iOS device")
                print("2. Tap '+' → 'Add Accessory'")
                print("3. Tap 'More Options...' at the bottom")
                print("4. Look for 'NFC Lock' in the nearby accessories")
                print("5. If not found, tap 'Enter Code Manually'")
                print(f"6. Enter the PIN: {setup_code}")
                print("7. Follow the setup instructions")
                
                if setup_uri:
                    print(f"\n🔗 Setup URI: {setup_uri}")
                    
                    # Try to show QR code if available
                    if QR_AVAILABLE:
                        try:
                            print("\n🔲 QR Code (ASCII):")
                            # Create QR code without PIL dependency
                            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=1,
                                border=2,
                            )
                            qr.add_data(setup_uri)
                            qr.make(fit=True)
                            
                            # Print ASCII QR code to terminal
                            qr.print_ascii(invert=True)
                            
                        except Exception as e:
                            print(f"⚠️  QR code generation failed: {e}")
                            print("💡 Use the Setup PIN above instead")
                    else:
                        print("\n💡 QR Code not available (qrcode package not installed)")
                        print("   Install with: pip install qrcode")
                        print("   Or use the Setup PIN above")
                else:
                    print("⚠️  No setup URI available")
            else:
                print("❌ No setup code available. Device may already be paired.")
                print("\n💡 To get a new setup code:")
                print("1. Reset pairing: python3 reconnect_homekit.py --reset-pairing")
                print("2. Start the service: python3 main.py")
                print("3. Look for the setup code in the console output")
                
        except Exception as e:
            print(f"❌ Error getting setup information: {e}")
            print("\n🔧 Troubleshooting:")
            print("• Make sure the configuration file exists")
            print("• Try resetting the pairing first")
            print("• Ensure the service is not already running")
            print("• If you see 'setup_uri' errors, restart the main application:")
            print("  1. Stop any running instances of main.py")
            print("  2. Run: python3 main.py")
            print("  3. Look for the setup code in console output")
    
    def restart_service(self):
        """Restart the HomeKit service with current configuration"""
        print("\n🔄 Restarting HomeKit Service...")
        print("=" * 35)
        
        try:
            # Check if Home Key is configured
            homekey_file = self.config["homekey"]["persist"]
            if os.path.exists(homekey_file):
                repository = Repository(homekey_file)
                reader_key = repository.get_reader_private_key()
                
                if reader_key == bytes.fromhex("00" * 32):
                    print("❌ Home Key not configured. Please complete initial setup first.")
                    return
            
            print("✅ Starting HomeKit service...")
            print("🔧 Configuring components...")
            
            # Configure components
            nfc_device = configure_nfc_device(self.config["nfc"])
            homekey_service = configure_homekey_service(self.config["homekey"], nfc_device)
            hap_driver, accessory = configure_hap_accessory(self.config["hap"], homekey_service)
            
            print(f"🌐 HomeKit accessory available on port {self.config['hap']['port']}")
            print("📱 The accessory should now be discoverable in the Home app")
            print("\n⏹️  Press Ctrl+C to stop the service")
            
            # Start services
            homekey_service.start()
            hap_driver.start()
            
        except KeyboardInterrupt:
            print("\n🛑 Service stopped by user")
            try:
                homekey_service.stop()
                hap_driver.stop()
            except Exception:
                pass
        except Exception as e:
            print(f"❌ Error starting service: {e}")
    
    def repair_configuration(self):
        """Check and repair common configuration issues"""
        print("\n🔧 Checking Configuration...")
        print("=" * 35)
        
        issues_found = False
        
        # Check file permissions
        files_to_check = [
            self.config_path,
            self.config["hap"]["persist"],
            self.config["homekey"]["persist"]
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                if not os.access(file_path, os.R_OK | os.W_OK):
                    print(f"❌ Permission issue with file: {file_path}")
                    issues_found = True
        
        # Check port availability
        port = self.config["hap"]["port"]
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    print(f"⚠️  Port {port} is already in use")
                    issues_found = True
        except Exception:
            pass
        
        if not issues_found:
            print("✅ No configuration issues found")
        else:
            print("\n🔧 Please resolve the issues above and try again")


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
        "--restart-service", 
        action="store_true",
        help="Restart the HomeKit service with current configuration"
    )
    
    parser.add_argument(
        "--show-qr", 
        action="store_true",
        help="Show the HomeKit setup QR code"
    )
    
    parser.add_argument(
        "--repair-config", 
        action="store_true",
        help="Check and repair common configuration issues"
    )
    
    parser.add_argument(
        "--config", 
        default="configuration.json",
        help="Path to configuration file (default: configuration.json)"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    try:
        reconnector = HomeKitReconnector(args.config)
        
        print("🍎 Apple Home Key Reader - HomeKit Reconnection Tool")
        print("=" * 55)
        
        if args.check_status:
            reconnector.check_status()
        
        if args.reset_pairing:
            reconnector.reset_pairing()
        
        if args.show_qr:
            reconnector.show_setup_qr()
        
        if args.restart_service:
            reconnector.restart_service()
            
        if args.repair_config:
            reconnector.repair_configuration()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
