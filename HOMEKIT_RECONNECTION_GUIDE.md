# HomeKit Connection Guide

This guide covers both reconnecting to HomeKit and adding new devices to your Apple Home Key Reader setup.

## Tools Available

### 1. Reconnection Tools (for lost connections)
- `reconnect_homekit.py` - Full featured reconnection tool with QR codes
- `reconnect_homekit_standalone.py` - Lightweight tool with minimal dependencies

### 2. Add New Device Tools (preserves existing pairings)
- `add_new_device.py` - Full featured tool for adding new iOS devices
- `add_new_device_simple.py` - Simple tool with minimal dependencies

## When to Use Each Tool

### Use Reconnection Tools When:
- Your HomeKit connection was lost after a system restart
- You can't see the lock in the Home app anymore
- The Home app shows "No Response" for your lock
- You want to add the lock to a different HomeKit home
- You've reset your iOS device and need to re-pair

### Use Add New Device Tools When:
- You want to add a new iPhone or iPad to your existing setup
- You got a new device and want to access the lock
- Someone in your family needs access to the lock
- You want to keep all existing pairings while adding new ones

## Quick Start

### Adding a New Device (Recommended)

If you want to add a new iPhone/iPad while keeping existing devices working:

```bash
# Simple version (minimal dependencies)
python3 add_new_device_simple.py

# Full version (with QR codes)
python3 add_new_device.py --show-qr
```

### Reconnecting After Connection Loss

If your existing devices lost connection to HomeKit:

```bash
# Quick status check
python3 reconnect_homekit.py --check-status

# Show QR code for reconnection
python3 reconnect_homekit.py --show-qr
```

## Prerequisites

1. Your Apple Home Key Reader was previously set up and working
2. Python 3.9+ is installed
3. All project dependencies are installed

## Installation

1. Install the additional requirements for the reconnection tool:
   ```bash
   pip install -r requirements_reconnect.txt
   ```
   
   Note: The QR code package now generates ASCII QR codes in the terminal (no PIL required).

## Usage Options

### 1. Check Current Status

First, check the current status of your HomeKit and Home Key configuration:

```bash
python3 reconnect_homekit.py --check-status
```

This will show you:
- Whether configuration files exist
- HomeKit pairing status
- Number of paired devices
- Home Key configuration details
- NFC device configuration

### 2. Show Setup QR Code

If your device is not paired, you can display the HomeKit setup QR code:

```bash
python3 reconnect_homekit.py --show-qr
```

This will show:
- The current HomeKit setup PIN (8-digit code)
- Step-by-step instructions for manual setup
- ASCII QR code displayed in the terminal (if qrcode package is installed)
- Setup URI for advanced users

**Note**: If you see an error about 'setup_uri' or 'setup_code', this means the HomeKit state needs to be refreshed. In this case:
1. Stop any running instances of the main application
2. Restart the main application: `python3 main.py`
3. Look for the setup code in the console output
4. Use that code to add the accessory in the Home app

For a lightweight option that shows the PIN without requiring all dependencies:

```bash
python3 reconnect_homekit_standalone.py --show-info
```

Then:
1. Open the Home app on your iOS device
2. Tap '+' and select "Add Accessory"  
3. Tap "More Options..." at the bottom
4. Look for "NFC Lock" in nearby accessories
5. If not found, tap "Enter Code Manually" and enter the 8-digit PIN
6. Follow the setup instructions

### 3. Restart HomeKit Service

If everything is configured but the connection isn't working, restart the service:

```bash
python3 reconnect_homekit.py --restart-service
```

This will:
- Verify your Home Key is configured
- Start the HomeKit service
- Make the accessory discoverable
- Keep running until you press Ctrl+C

### 4. Reset HomeKit Pairing

If you need to start fresh (removes all pairings):

```bash
python3 reconnect_homekit.py --reset-pairing
```

⚠️ **Warning**: This removes all HomeKit pairings. You'll need to set up the accessory again in the Home app.

### 5. Check Configuration Issues

Diagnose common configuration problems:

```bash
python3 reconnect_homekit.py --repair-config
```

## Common Scenarios

### Scenario 1: "No Response" in Home App

**Symptoms**: Lock appears in Home app but shows "No Response"

**Solution**:
1. Check status: `python3 reconnect_homekit.py --check-status`
2. Restart service: `python3 reconnect_homekit.py --restart-service`
3. Make sure your device is on the same network

### Scenario 2: Lock Disappeared from Home App

**Symptoms**: Lock no longer appears in the Home app

**Solutions**:
1. Check if pairing still exists: `python3 reconnect_homekit.py --check-status`
2. If paired devices = 0, show QR code: `python3 reconnect_homekit.py --show-qr`
3. Re-add the accessory using the Home app

### Scenario 3: Complete Reset Needed

**Symptoms**: Nothing works, need to start over

**Solution**:
1. Reset pairing: `python3 reconnect_homekit.py --reset-pairing`
2. Restart main application: `python3 main.py`
3. Add accessory in Home app using the setup code/QR

### Scenario 4: Moving to Different HomeKit Home

**Symptoms**: Want to move the lock to a different HomeKit home

**Solution**:
1. Remove from current home in the Home app
2. Reset pairing: `python3 reconnect_homekit.py --reset-pairing`
3. Add to new home using setup code

## Troubleshooting

### Setup Code/URI Errors
If you see errors like "'State' object has no attribute 'setup_uri'" or "'State' object has no attribute 'setup_code'":
1. This means the HomeKit state file is outdated or incompatible
2. Stop any running instances of `main.py`
3. Optionally backup the current `hap.state` file
4. Restart the main application: `python3 main.py`
5. Look for the new setup code in the console output
6. Use the new code to add the accessory in the Home app

### Port Already in Use
If you get a "port already in use" error:
1. Stop any running instances of `main.py`
2. Check what's using the port: `netstat -an | findstr :51926` (Windows) or `lsof -i :51926` (Linux/Mac)
3. Change the port in `configuration.json` if needed

### Permission Errors
If you get permission errors:
1. Run the script with appropriate permissions
2. Check file ownership of configuration files
3. Make sure Python can read/write the configuration directory

### NFC Device Issues
If NFC isn't working:
1. Check the device path in `configuration.json`
2. Verify NFC hardware is connected
3. Run the status check to see current configuration

### Network Discovery Issues
If the Home app can't find the accessory:
1. Ensure your iOS device and the reader are on the same network
2. Check firewall settings on the reader device
3. Try restarting both devices
4. Make sure the port (default 51926) isn't blocked

## Manual Setup Alternative

If the reconnection script doesn't work, you can manually set up HomeKit again:

1. Stop any running services
2. Delete the HAP state file (usually `hap.state`)
3. Run the main application: `python3 main.py`
4. Look for setup information in the console output
5. Add the accessory manually in the Home app

## Getting Help

If you continue to have issues:
1. Check the main project README for setup instructions
2. Verify your hardware setup (NFC device, connections)
3. Check the project's GitHub issues for similar problems
4. Make sure all dependencies are correctly installed

## Adding New Devices (Without Affecting Existing Ones)

### Why Use the Add New Device Tools?

Instead of resetting your entire HomeKit setup (which removes all existing device pairings), these tools let you add new iOS devices while preserving all existing access.

### Tool Options

#### Simple Tool (Minimal Dependencies)
```bash
python3 add_new_device_simple.py
```

This tool:
- Works even without HAP-python installed
- Shows basic setup information
- Provides step-by-step instructions

#### Full Tool (Complete Features)
```bash
# Show basic information
python3 add_new_device.py

# Include QR code for easy scanning
python3 add_new_device.py --show-qr

# Check system status first
python3 add_new_device.py --status
```

This tool provides:
- Current setup code validation
- QR code generation (requires `qrcode` package)
- Comprehensive status checking
- Detailed troubleshooting information

### Step-by-Step Process

1. **Run the add new device tool:**
   ```bash
   python3 add_new_device.py --show-qr
   ```

2. **On your NEW iOS device:**
   - Open the Home app
   - Tap '+' (top right corner)
   - Select 'Add Accessory'
   - Tap 'More Options...'

3. **Choose your method:**
   - **Method A**: Look for 'NFC Lock' in nearby accessories
   - **Method B**: Tap 'Enter Code Manually' and enter the displayed setup code
   - **Method C**: Scan the QR code (if shown)

4. **Complete setup:**
   - Follow the Home app setup wizard
   - Test access with your new device

### Important Notes

✅ **Safe Operation**: This process preserves all existing device pairings
✅ **No Disruption**: Current users keep their access
✅ **No File Deletion**: The hap.state file remains intact
✅ **Multiple Devices**: You can add as many devices as needed

### Troubleshooting New Device Addition

#### Problem: No setup code displayed
**Solution**: Ensure the main service is running (`python3 main.py`)

#### Problem: "Invalid setup code" error
**Check**: Setup codes must be exactly 8 numeric digits
**Solution**: Restart the main service to generate a new code

#### Problem: Accessory not found in Home app
**Check**: Both devices on same WiFi network
**Solution**: Make sure port is not blocked by firewall

#### Problem: Setup fails during pairing
**Check**: Console output of main service for errors
**Solution**: Restart main service and try again

## Files Created/Modified

This guide includes these tools:

### Reconnection Tools
- `reconnect_homekit.py` - Full featured reconnection tool with QR codes
- `reconnect_homekit_standalone.py` - Lightweight tool with minimal dependencies
- `reconnect_homekit.bat` / `reconnect_homekit.sh` - Interactive menu scripts

### Add New Device Tools
- `add_new_device.py` - Full featured tool for adding new iOS devices
- `add_new_device_simple.py` - Simple tool with minimal dependencies

### Dependencies
- `requirements_reconnect.txt` - Additional packages for QR code support

### Backup Files
The reconnection script may create these files:
- `hap.state.backup.TIMESTAMP` - Backup of previous HomeKit pairings
- These backups can be restored by renaming back to `hap.state` if needed

## Security Notes

- HomeKit pairing data contains security keys - keep backups secure
- Only reset pairings when necessary
- The setup code should only be shared with trusted users
- QR codes contain the setup URI - don't share screenshots publicly
