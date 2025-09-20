#!/usr/bin/env python3
"""
HomeKit Setup Code Finder

This script helps you find the HomeKit setup code for pairing new devices.
"""

import sys
import json
import os
import subprocess
import re

def find_setup_code_in_logs():
    """Try to find setup code in recent logs"""
    print("🔍 Searching for setup code in system logs...")
    
    # Common log patterns where HAP setup code might appear
    log_patterns = [
        "Setup code:",
        "setup_id",
        "Setup ID:",
        "QR Code:",
        "X-HM://",
        "homekit setup",
        "pairing code"
    ]
    
    # Try different log sources
    log_commands = [
        "journalctl --no-pager -n 100 | grep -i homekit",
        "journalctl --no-pager -n 100 | grep -i setup",
        "journalctl --no-pager -n 100 | grep -E '[0-9]{3}-[0-9]{2}-[0-9]{3}'",
        "tail -n 100 /var/log/syslog 2>/dev/null | grep -i homekit",
    ]
    
    found_codes = []
    
    for cmd in log_commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # Look for setup code pattern (XXX-XX-XXX)
                    setup_match = re.search(r'\b(\d{3}-\d{2}-\d{3})\b', line)
                    if setup_match:
                        found_codes.append(setup_match.group(1))
                    
                    # Look for QR URI pattern
                    qr_match = re.search(r'X-HM://(\w+)', line)
                    if qr_match:
                        setup_id = qr_match.group(1)
                        if len(setup_id) >= 8:
                            formatted = f"{setup_id[:3]}-{setup_id[3:5]}-{setup_id[5:]}"
                            found_codes.append(formatted)
        except:
            continue
    
    return list(set(found_codes))  # Remove duplicates

def check_hap_state():
    """Check HAP state for pairing information"""
    hap_state_file = "hap.state"
    
    if not os.path.exists(hap_state_file):
        return None
    
    try:
        with open(hap_state_file, 'r') as f:
            state = json.load(f)
        
        return {
            'paired': state.get('paired', False),
            'paired_clients': state.get('paired_clients', {}),
            'setup_id': state.get('setup_id', None),
            'mac': state.get('mac', None),
            'config_version': state.get('config_version', None)
        }
    except:
        return None

def generate_manual_instructions():
    """Provide manual instructions to find setup code"""
    print("\n📖 Manual Setup Code Location Guide")
    print("=" * 50)
    print("The HomeKit setup code appears when your HAP service starts.")
    print("Here's how to find it:")
    print()
    print("1. 🔍 Check your service logs:")
    print("   sudo journalctl -u your-homekey-service -f")
    print("   (Look for lines containing setup code or QR code)")
    print()
    print("2. 📱 If running manually, restart your main script:")
    print("   python main.py")
    print("   (The setup code should appear in the console output)")
    print()
    print("3. 🖥️ Check the console where your HomeKey service is running")
    print("   (Look for output like 'Setup Code: XXX-XX-XXX')")
    print()
    print("4. 📋 The setup code format is: XXX-XX-XXX (8 digits total)")
    print("   Example: 123-45-678")
    print("=" * 50)

def show_current_status():
    """Show current HAP status"""
    print("📊 Current HomeKit Status")
    print("=" * 30)
    
    state = check_hap_state()
    if state:
        print(f"🔄 Paired: {'Yes' if state['paired'] else 'No'}")
        print(f"👥 Paired Clients: {len(state['paired_clients'])}")
        print(f"🏷️ MAC Address: {state['mac']}")
        print(f"⚙️ Config Version: {state['config_version']}")
        
        if state['setup_id']:
            setup_id = state['setup_id']
            formatted = f"{setup_id[:3]}-{setup_id[3:5]}-{setup_id[5:]}"
            print(f"📋 Setup Code: {formatted}")
            print(f"🔗 QR URI: X-HM://{setup_id}")
        else:
            print("📋 Setup Code: Not available in state file")
    else:
        print("❌ Could not read HAP state")
    
    print("=" * 30)

def main():
    """Main script entry point"""
    print("🔍 HomeKit Setup Code Finder")
    print("=" * 40)
    
    # Show current status
    show_current_status()
    
    # Look for setup codes in logs
    print("\n🔍 Searching logs for setup codes...")
    found_codes = find_setup_code_in_logs()
    
    if found_codes:
        print(f"\n✅ Found {len(found_codes)} potential setup code(s):")
        for i, code in enumerate(found_codes, 1):
            print(f"   {i}. {code}")
            qr_uri = f"X-HM://{code.replace('-', '')}"
            print(f"      QR URI: {qr_uri}")
        
        print(f"\n💡 Use any of these codes to pair new HomeKit devices")
    else:
        print("\n⚠️ No setup codes found in recent logs")
    
    # Check if device needs pairing mode
    state = check_hap_state()
    if state and state['paired'] and state['paired_clients']:
        print(f"\n💡 Your device has {len(state['paired_clients'])} paired client(s)")
        print("   To add more controllers, you may need to enable pairing mode")
        print("   Try: python enable_pairing_mode.py")
    elif state and not state['paired']:
        print("\n💡 Your device appears to be in pairing mode already")
        print("   The setup code should be visible in your service logs")
    
    # Provide manual instructions
    generate_manual_instructions()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())