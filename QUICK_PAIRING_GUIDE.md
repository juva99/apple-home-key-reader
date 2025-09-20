# Quick HomeKit Re-Pairing Guide

Since your Apple HomeKey Reader is already running and working (as shown by the HAP connections), here are the simplest ways to enable pairing mode for additional HomeKit controllers:

## 🚀 **Method 1: Simple Pairing Mode Script (Recommended)**

Use the standalone pairing enabler script:

```bash
# Enable pairing mode for 10 minutes (600 seconds)
python enable_pairing_mode.py

# Enable pairing mode for custom duration (e.g., 5 minutes)
python enable_pairing_mode.py 300
```

This script:
- ✅ Works with your existing running service
- ✅ Shows the setup code and QR URI
- ✅ Temporarily enables pairing mode
- ✅ Automatically restores normal operation
- ✅ Can be cancelled with Ctrl+C

## 🔧 **Method 2: Using the Re-Pairing Script**

If the main pairing script gets stuck at "Starting HAP driver", it's because your service is already running. You have two options:

### Option A: Stop the main service first
```bash
# Stop your main service (if running as systemd service)
sudo systemctl stop apple-homekey-reader

# Then run the pairing script
python pair_device.py --timeout 300 --duration 600

# Restart your main service after pairing
sudo systemctl start apple-homekey-reader
```

### Option B: Use the simple script instead
```bash
# Just use the simple pairing enabler while service is running
python enable_pairing_mode.py 600
```

## 📱 **Pairing Process**

Once pairing mode is enabled:

1. **Open the Home app** on your new iPhone/iPad
2. **Tap the "+" button** → "Add Accessory"
3. **Choose one of these options:**
   - Enter the setup code: `XXX-XX-XXX` (displayed by the script)
   - Scan a QR code generated from the URI: `X-HM://XXXXXXXX`
   - Use "More options" if the accessory doesn't appear automatically

## 🔍 **Troubleshooting Your Current Issue**

Based on your logs, your HAP service is running correctly:
- ✅ HAP driver loaded state from `hap.state`
- ✅ Accessory started on port 51926
- ✅ HomeKit controller (10.0.0.64) connected successfully
- ✅ Lock characteristics are working

The script gets stuck because:
1. Your service is already running and listening on the HAP port
2. The script tries to start another HAP driver instance
3. This creates a conflict or blocking situation

## 💡 **Quick Solution**

**Use the simple script while your service is running:**

```bash
python enable_pairing_mode.py 600
```

This will:
1. Show your current setup code
2. Temporarily enable pairing mode for 10 minutes
3. Allow new HomeKit controllers to pair
4. Automatically restore normal operation

## 🛡️ **Safety Notes**

- ✅ Existing HomeKit controllers remain functional
- ✅ NFC functionality continues working  
- ✅ Lock operation is not disrupted
- ✅ Pairing mode automatically times out for security

The simple approach is safer and less disruptive than stopping/starting your main service!