# HomeKit Reconnection Tools - Quick Reference

This document provides a quick overview of the HomeKit reconnection tools created for your Apple Home Key Reader project.

## Files Created

### 1. `reconnect_homekit_standalone.py` (Recommended)
- **Purpose**: Main reconnection tool that works even without all project dependencies
- **Features**: Status check, pairing reset, setup info, service verification
- **Usage**: `python3 reconnect_homekit_standalone.py --check-status`

### 2. `reconnect_homekit.py` (Advanced)
- **Purpose**: Full-featured tool with QR code generation and service restart
- **Requires**: All project dependencies installed (HAP-python, etc.)
- **Features**: Everything from standalone + QR codes + service restart

### 3. `reconnect_homekit.bat` (Windows)
- **Purpose**: Interactive menu for Windows users
- **Usage**: Double-click to run, provides simple menu interface

### 4. `reconnect_homekit.sh` (Linux/macOS)
- **Purpose**: Interactive menu for Unix-like systems
- **Usage**: `./reconnect_homekit.sh` (make executable first)

### 5. `requirements_reconnect.txt`
- **Purpose**: Additional dependencies for QR code generation (ASCII output only)
- **Install**: `pip install -r requirements_reconnect.txt`
- **Note**: No PIL dependency required - uses terminal ASCII output

### 6. `HOMEKIT_RECONNECTION_GUIDE.md`
- **Purpose**: Comprehensive guide with troubleshooting steps
- **Content**: Detailed scenarios, solutions, and explanations

## Quick Start

### Check Current Status
```bash
python3 reconnect_homekit_standalone.py --check-status
```

### Reset HomeKit Pairing
```bash
python3 reconnect_homekit_standalone.py --reset-pairing
```

### Show Setup PIN and Instructions
```bash
python3 reconnect_homekit_standalone.py --show-info
```

### Show QR Code (if available)
```bash
python3 reconnect_homekit.py --show-qr
```

## When to Use Each Tool

- **Lost HomeKit connection**: Use `--check-status` first
- **"No Response" in Home app**: Restart the main application (`python3 main.py`)
- **Lock disappeared from Home app**: Use `--reset-pairing` then re-add in Home app
- **Need setup PIN**: Use `--show-info` for lightweight PIN display
- **Need QR code**: Install requirements_reconnect.txt and use `--show-qr` for ASCII QR
- **Want guided help**: Use the .bat (Windows) or .sh (Linux/macOS) interactive scripts

## Key Features

✅ **PIN display**: Shows current HomeKit setup PIN without requiring all dependencies  
✅ **ASCII QR codes**: Terminal-based QR codes without PIL dependency  
✅ **Status checking**: Verify configuration files and pairing status  
✅ **Safe reset**: Automatic backup before removing pairing data  
✅ **Cross-platform**: Works on Windows, Linux, and macOS  
✅ **User-friendly**: Clear instructions and emoji indicators  
✅ **Interactive menus**: Batch/shell scripts for easy access  

## Integration

The tools are designed to work alongside your existing Apple Home Key Reader:

1. **No interference**: Tools only read/modify HomeKit pairing data, not Home Key data
2. **Safe operation**: Always create backups before making changes
3. **Clear guidance**: Provide step-by-step instructions for reconnection
4. **Status visibility**: Show exactly what's configured and what's missing

## Error Handling

- **Missing dependencies**: Clear error messages with installation instructions
- **File permissions**: Checks and reports file access issues
- **Port conflicts**: Detects if HomeKit port is already in use
- **Configuration errors**: Validates JSON configuration files

The tools make it easy for users to reconnect to HomeKit without needing to understand the internals of HAP-python or the Home Key protocol.
