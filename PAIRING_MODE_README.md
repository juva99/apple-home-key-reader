# HomeKit Re-Pairing Functionality

This document explains the new re-pairing functionality that allows you to pair additional HomeKit controllers to your Apple HomeKey Reader even when the `hap.state` file already exists.

## Overview

Previously, once the HomeKit Accessory Protocol (HAP) state file existed, the device would reject new pairing attempts for security reasons. This implementation adds a "pairing mode" that temporarily allows new pairings while preserving existing controller connections.

## Features

- **Preserve Existing Pairings**: All previously paired HomeKit controllers remain functional
- **Temporary Pairing Mode**: Automatically disables after a specified duration
- **Manual Control**: Can be enabled/disabled programmatically
- **Multiple Controllers**: Supports pairing additional HomeKit controllers
- **Safe Operation**: Automatically restores original pairing state when disabled

## Usage Methods

### 1. Programmatic Control

```python
# Enable pairing mode for 5 minutes (300 seconds) and show QR code
service.enable_pairing_mode(300, show_pairing_info=True)

# Check if pairing mode is active
if service.is_pairing_mode_active():
    print("Pairing mode is active - new controllers can pair")

# Get pairing information programmatically
pairing_info = service.get_pairing_info()
if pairing_info:
    print(f"Setup Code: {pairing_info['formatted_setup_code']}")
    print(f"QR URI: {pairing_info['qr_uri']}")

# Display formatted pairing information with QR code
service.print_pairing_info()

# Disable pairing mode manually
service.disable_pairing_mode()
```

### 2. NFC Pairing Session

```python
# Start a complete pairing session with automatic pairing mode and QR display
success = service.pair_new_device(timeout_seconds=60, enable_pairing_mode=True, show_pairing_info=True)
if success:
    print("New device paired successfully!")
```

### 3. HomeKit Lock Control Point

You can trigger pairing mode through the HomeKit app using specific byte sequences sent to the Lock Control Point characteristic:

- **Enable pairing mode**: Send `[0xFF, duration_high_byte, duration_low_byte]`
- **Disable pairing mode**: Send `[0x00]`

Examples:

- `[0xFF, 0x01, 0x2C]` = Enable for 300 seconds (0x012C)
- `[0xFF, 0x02, 0x58]` = Enable for 600 seconds (0x0258)
- `[0x00]` = Disable pairing mode

## Implementation Details

### Accessory (accessory.py) Changes

Added pairing mode state management:

- `_pairing_mode`: Boolean flag for current state
- `_pairing_mode_timer`: Timer for automatic disable
- `_pairing_mode_duration`: Configurable timeout duration

Key methods:

- `enable_pairing_mode(duration_seconds=300, show_pairing_info=True)`: Enable with auto-timeout and optional QR display
- `disable_pairing_mode()`: Manual disable
- `is_pairing_mode_active()`: Status check
- `get_pairing_info()`: Get setup code and QR URI information
- `print_pairing_info()`: Display formatted pairing information with QR code
- `_start_pairing_mode_timer()`: Internal timer management
- `_cancel_pairing_mode_timer()`: Internal timer cleanup

### Service (service.py) Changes

Added accessory reference and delegation methods:

- `set_accessory_reference(accessory)`: Link service to accessory
- `enable_pairing_mode(duration_seconds=300, show_pairing_info=True)`: Delegate to accessory with QR display option
- `disable_pairing_mode()`: Delegate to accessory
- `is_pairing_mode_active()`: Delegate to accessory
- `get_pairing_info()`: Get pairing information from accessory
- `print_pairing_info()`: Display pairing information via accessory

Updated `pair_new_device()` to optionally enable pairing mode and show QR information.

### Main Application (main.py) Changes

Modified `configure_hap_accessory()` to establish the service ↔ accessory reference:

```python
# Set the accessory reference in the service for pairing mode control
if homekey_service:
    homekey_service.set_accessory_reference(accessory)
```

## Security Considerations

1. **Temporary Nature**: Pairing mode automatically disables after the specified duration
2. **Existing Pairings Preserved**: No existing controllers are removed or affected
3. **Manual Override**: Can be disabled immediately if needed
4. **State Restoration**: Original pairing state is restored when pairing mode ends

## How It Works

1. When pairing mode is enabled, the HAP driver's `paired` state is temporarily set to `False`
2. This allows new controllers to initiate pairing while existing controllers remain in the state
3. A timer automatically restores the original `paired` state after the specified duration
4. The original pairing state is also restored if pairing mode is manually disabled

## Example Usage Scenarios

### Scenario 1: Adding a New iPhone

```python
# Enable pairing mode for 5 minutes and show QR code
service.enable_pairing_mode(300, show_pairing_info=True)

# This will display:
# - Setup code (e.g., 123-45-678)
# - QR code URI (X-HM://12345678)
# - ASCII QR code (if supported)
# - Instructions for pairing

# User opens Home app on new iPhone and scans QR code or enters setup code
# Pairing completes successfully
# Pairing mode automatically disables after 5 minutes
```

### Scenario 2: Family Member's Device

```python
# Start a guided pairing session with QR code display
success = service.pair_new_device(timeout_seconds=120, enable_pairing_mode=True, show_pairing_info=True)
if success:
    print("Family member's device added successfully!")
else:
    print("Pairing timeout - please try again")
```

### Scenario 3: Replacing a Device

```python
# Enable pairing mode via HomeKit app using Lock Control Point
# Send bytes [0xFF, 0x02, 0x58] to enable for 10 minutes
# Remove old device from Home app
# Add new device to Home app
# Pairing mode automatically disables
```

## Compatibility

- Works with existing `hap.state` files
- Compatible with all HomeKit controllers (iPhone, iPad, Mac, Apple Watch, HomePod)
- No changes required to existing paired devices
- Backward compatible with existing HomeKey NFC functionality

## Troubleshooting

### Pairing Mode Won't Enable

- Check that accessory reference is set: `service.set_accessory_reference(accessory)`
- Verify HAP driver is initialized and accessible
- Check logs for error messages

### New Controller Won't Pair

- Ensure pairing mode is active: `service.is_pairing_mode_active()`
- Check that pairing mode hasn't timed out
- Verify HomeKit setup code or QR code is correct
- Ensure new controller isn't already paired to another HomeKit hub

### Existing Controllers Stop Working

- This shouldn't happen - contact support if existing controllers are affected
- Try disabling and re-enabling pairing mode
- Check HomeKit network connectivity

## Example Code

See `example_pairing_usage.py` for complete working examples of all functionality.
