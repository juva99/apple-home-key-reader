# HomeKit Reconnection Guide

This guide helps you reconnect your Apple Home Key Reader to HomeKit after the initial setup has been completed.

## When to Use This Guide

Use this reconnection script when:
- Your HomeKit connection was lost after a system restart
- You can't see the lock in the Home app anymore
- The Home app shows "No Response" for your lock
- You want to add the lock to a different HomeKit home
- You've reset your iOS device and need to re-pair

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

## Files Created/Modified

The reconnection script may create these files:
- `hap.state.backup.TIMESTAMP` - Backup of previous HomeKit pairings
- These backups can be restored by renaming back to `hap.state` if needed

## Security Notes

- HomeKit pairing data contains security keys - keep backups secure
- Only reset pairings when necessary
- The setup code should only be shared with trusted users
- QR codes contain the setup URI - don't share screenshots publicly
