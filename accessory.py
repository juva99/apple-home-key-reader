import threading
import functools
import logging
import time

# Add GPIO import
try:
    from gpiozero import LED

    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.getLogger().warning("RPi.GPIO not available - GPIO functionality disabled")

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_DOOR_LOCK

from service import Service

log = logging.getLogger()


# Lock class performs no logic, forwarding requests to Service class
class Lock(Accessory):
    category = CATEGORY_DOOR_LOCK

    def __init__(
        self,
        *args,
        service: Service,
        lock_state_at_startup=1,
        gpio_pin: int = None,
        gpio_duration: float = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._last_client_public_keys = None
        
        # Add pairing mode state
        self._pairing_mode = False
        self._pairing_mode_timer = None
        self._pairing_mode_duration = 300  # 5 minutes default

        # Gate lock is always locked by default (1 = locked, 0 = unlocked)
        self._lock_target_state = 1
        self._lock_current_state = 1
        self._auto_lock_timer = None

        self.service = service
        self.service.on_endpoint_authenticated = self.on_endpoint_authenticated

        # GPIO configuration - use lock_timeout as default duration
        log.info(f"Configuring GPIO pin {gpio_pin}")
        self.gpio_pin = gpio_pin
        self.gpio_duration = (
            gpio_duration if gpio_duration is not None else service.lock_timeout
        )

        if self.gpio_pin is not None and GPIO_AVAILABLE:
            log.info(f"GPIO pin {self.gpio_pin} configured for unlock signaling")
        elif self.gpio_pin is not None and not GPIO_AVAILABLE:
            log.warning("GPIO pin configured but RPi.GPIO not available")

        self.add_lock_service()
        self.add_nfc_access_service()
        self.add_unpair_hook()

    def _trigger_gpio_unlock(self):
        """Raise GPIO pin high for the configured duration"""
        if self.gpio_pin is None or not GPIO_AVAILABLE:
            log.info(self.gpio_pin)
            return

        def gpio_unlock_thread():
            try:
                log.info(
                    f"Triggering GPIO pin {self.gpio_pin} HIGH for {self.gpio_duration}s"
                )
                relay = LED(self.gpio_pin)
                log.info(f"GPIO pin {self.gpio_pin} set to HIGH")
                time.sleep(self.gpio_duration)
                log.info(f"Setting GPIO pin {self.gpio_pin} back to LOW")
                del relay
                log.info(f"GPIO pin {self.gpio_pin} returned to LOW")
            except Exception as e:
                log.error(f"Failed to control GPIO pin {self.gpio_pin}: {e}")

        # Run GPIO control in separate thread to avoid blocking
        gpio_thread = threading.Thread(target=gpio_unlock_thread, daemon=True)
        gpio_thread.start()

    def _cancel_auto_lock_timer(self):
        """Cancel any existing auto-lock timer"""
        if self._auto_lock_timer is not None:
            self._auto_lock_timer.cancel()
            self._auto_lock_timer = None

    def _start_auto_lock_timer(self):
        """Start the auto-lock timer"""
        self._cancel_auto_lock_timer()

        def auto_lock():
            log.info(f"Auto-locking after {self.service.lock_timeout} seconds")
            self._lock_target_state = 1
            self._lock_current_state = 1
            self.lock_target_state.set_value(
                self._lock_target_state, should_notify=True
            )
            self.lock_current_state.set_value(
                self._lock_current_state, should_notify=True
            )
            print("locked (auto)")
            self._auto_lock_timer = None

        self._auto_lock_timer = threading.Timer(self.service.lock_timeout, auto_lock)
        self._auto_lock_timer.start()

    def enable_pairing_mode(self, duration_seconds=300, show_pairing_info=True):
        """
        Enable pairing mode to allow new HomeKit controllers to pair.
        This temporarily allows new pairings while preserving existing ones.
        
        Args:
            duration_seconds: How long to keep pairing mode active
            show_pairing_info: Whether to display QR code and setup information
        """
        if self._pairing_mode:
            log.info("Pairing mode already active, extending duration")
            self._cancel_pairing_mode_timer()
        else:
            log.info(f"Enabling pairing mode for {duration_seconds} seconds")
            self._pairing_mode = True
            
            # Enable pairing in the HAP driver
            if hasattr(self.driver, 'state'):
                # Temporarily allow new pairings
                original_paired = self.driver.state.paired
                self.driver.state.paired = False
                
                def restore_paired_state():
                    self.driver.state.paired = original_paired
                    self._pairing_mode = False
                    log.info("Pairing mode disabled - no longer accepting new pairings")
                
                # Store the restore function for manual cancellation
                self._restore_paired_state = restore_paired_state
            
        # Set timer to automatically disable pairing mode
        self._pairing_mode_duration = duration_seconds
        self._start_pairing_mode_timer()
        
        # Display pairing information if requested
        if show_pairing_info:
            self.print_pairing_info()
        
        return True

    def disable_pairing_mode(self):
        """Manually disable pairing mode"""
        if not self._pairing_mode:
            log.info("Pairing mode is not active")
            return False
            
        log.info("Manually disabling pairing mode")
        self._cancel_pairing_mode_timer()
        
        if hasattr(self, '_restore_paired_state'):
            self._restore_paired_state()
            del self._restore_paired_state
            
        return True

    def _start_pairing_mode_timer(self):
        """Start the pairing mode timer"""
        self._cancel_pairing_mode_timer()
        
        def auto_disable_pairing():
            log.info(f"Auto-disabling pairing mode after {self._pairing_mode_duration} seconds")
            if hasattr(self, '_restore_paired_state'):
                self._restore_paired_state()
                del self._restore_paired_state
            self._pairing_mode_timer = None
        
        self._pairing_mode_timer = threading.Timer(self._pairing_mode_duration, auto_disable_pairing)
        self._pairing_mode_timer.start()

    def _cancel_pairing_mode_timer(self):
        """Cancel any existing pairing mode timer"""
        if self._pairing_mode_timer is not None:
            self._pairing_mode_timer.cancel()
            self._pairing_mode_timer = None

    def is_pairing_mode_active(self):
        """Check if pairing mode is currently active"""
        return self._pairing_mode

    def get_pairing_info(self):
        """Get current pairing information including setup code and QR URI"""
        if hasattr(self.driver, 'state') and hasattr(self.driver.state, 'setup_id'):
            setup_code = self.driver.state.setup_id
            # Generate the HomeKit QR code URI
            qr_uri = f"X-HM://{setup_code}"
            return {
                'setup_code': setup_code,
                'qr_uri': qr_uri,
                'formatted_setup_code': f"{setup_code[:3]}-{setup_code[3:5]}-{setup_code[5:]}"
            }
        return None

    def print_pairing_info(self):
        """Print pairing information in a user-friendly format"""
        info = self.get_pairing_info()
        if info:
            print("\n🔗 HomeKit Pairing Information")
            print("=" * 50)
            print(f"Setup Code: {info['formatted_setup_code']}")
            print(f"QR Code URI: {info['qr_uri']}")
            print("\n📱 To pair with HomeKit:")
            print("1. Open the Home app on your iOS device")
            print("2. Tap '+' to add an accessory")
            print("3. Choose 'Add Accessory'")
            print("4. Either:")
            print(f"   - Enter setup code: {info['formatted_setup_code']}")
            print("   - Scan this QR code URI in a QR generator and scan it")
            print("   - Or use the camera to scan if QR code is displayed")
            print("=" * 50)
            
            # Try to trigger the HAP driver's QR code display
            if hasattr(self.driver, 'print_qrcode'):
                print("\n📋 QR Code:")
                try:
                    self.driver.print_qrcode()
                except Exception as e:
                    log.warning(f"Could not display QR code: {e}")
                    print(f"Use QR generator with URI: {info['qr_uri']}")
            else:
                print(f"\n📋 Generate QR code from URI: {info['qr_uri']}")
            
            return True
        else:
            print("⚠️ Pairing information not available (device may not be in pairing state)")
            return False

    def on_endpoint_authenticated(self, endpoint):
        log.info(f"Unlocking due to endpoint authentication: {endpoint}")
        self._lock_target_state = 0
        self._lock_current_state = 0
        self.lock_target_state.set_value(self._lock_target_state, should_notify=True)
        self.lock_current_state.set_value(self._lock_current_state, should_notify=True)
        print("unlocked (NFC)")

        # Trigger GPIO unlock
        self._trigger_gpio_unlock()

        # Start auto-lock timer
        self._start_auto_lock_timer()

    def add_unpair_hook(self):
        unpair = self.driver.unpair

        @functools.wraps(unpair)
        def patched_unpair(client_uuid):
            unpair(client_uuid)
            self.on_unpair(client_uuid)

        self.driver.unpair = patched_unpair

    def add_preload_service(self, service, chars=None, unique_id=None):
        """Create a service with the given name and add it to this acc."""
        if isinstance(service, str):
            service = self.driver.loader.get_service(service)
        if unique_id is not None:
            service.unique_id = unique_id
        if chars:
            chars = chars if isinstance(chars, list) else [chars]
            for char_name in chars:
                if isinstance(char_name, str):
                    char = self.driver.loader.get_char(char_name)
                    service.add_characteristic(char)
                else:
                    service.add_characteristic(char_name)
        self.add_service(service)
        return service

    def add_info_service(self):
        serv_info = self.driver.loader.get_service("AccessoryInformation")
        serv_info.configure_char("Name", value=self.display_name)
        serv_info.configure_char("SerialNumber", value="default")
        serv_info.add_characteristic(self.driver.loader.get_char("HardwareFinish"))
        serv_info.configure_char(
            "HardwareFinish", getter_callback=self.get_hardware_finish
        )
        self.add_service(serv_info)

    def add_lock_service(self):
        self.service_lock_mechanism = self.add_preload_service("LockMechanism")

        self.lock_current_state = self.service_lock_mechanism.configure_char(
            "LockCurrentState", getter_callback=self.get_lock_current_state, value=0
        )

        self.lock_target_state = self.service_lock_mechanism.configure_char(
            "LockTargetState",
            getter_callback=self.get_lock_target_state,
            setter_callback=self.set_lock_target_state,
            value=0,
        )

        self.service_lock_management = self.add_preload_service("LockManagement")

        self.lock_control_point = self.service_lock_management.configure_char(
            "LockControlPoint",
            setter_callback=self.set_lock_control_point,
        )

        self.lock_version = self.service_lock_management.configure_char(
            "Version",
            getter_callback=self.get_lock_version,
        )

    def add_nfc_access_service(self):
        self.service_nfc = self.add_preload_service("NFCAccess")

        self.char_nfc_access_supported_configuration = self.service_nfc.configure_char(
            "NFCAccessSupportedConfiguration",
            getter_callback=self.get_nfc_access_supported_configuration,
        )

        self.char_nfc_access_control_point = self.service_nfc.configure_char(
            "NFCAccessControlPoint",
            getter_callback=self.get_nfc_access_control_point,
            setter_callback=self.set_nfc_access_control_point,
        )

        self.configuration_state = self.service_nfc.configure_char(
            "ConfigurationState", getter_callback=self.get_configuration_state
        )

    def _update_hap_pairings(self):
        client_public_keys = set(self.clients.values())
        if self._last_client_public_keys == client_public_keys:
            return
        self._last_client_public_keys = client_public_keys
        self.service.update_hap_pairings(client_public_keys)

    def get_lock_current_state(self):
        log.info("get_lock_current_state")
        return self._lock_current_state

    def get_lock_target_state(self):
        log.info("get_lock_target_state")
        return self._lock_target_state

    def set_lock_target_state(self, value):
        log.info(f"set_lock_target_state {value}")
        self._lock_target_state = value
        self._lock_current_state = value
        self.lock_current_state.set_value(self._lock_current_state, should_notify=True)

        if value == 0:  # Unlocked manually via Home app
            print("unlocked (manual)")
            self._trigger_gpio_unlock()
            self._start_auto_lock_timer()
        else:  # Locked manually via Home app
            print("locked (manual)")
            self._cancel_auto_lock_timer()

        return self._lock_target_state

    def get_lock_version(self):
        log.info("get_lock_version")
        return ""

    def set_lock_control_point(self, value):
        log.info(f"set_lock_control_point: {value}")
        
        # Check if this is a pairing mode request (you can customize this logic)
        # For example, you could use a specific value to trigger pairing mode
        if value and len(value) > 0:
            # Example: if first byte is 0xFF, enable pairing mode
            if value[0] == 0xFF and len(value) > 1:
                duration = int.from_bytes(value[1:3], 'big') if len(value) >= 3 else 300
                self.enable_pairing_mode(duration)
            # Example: if first byte is 0x00, disable pairing mode
            elif value[0] == 0x00:
                self.disable_pairing_mode()

    # All methods down here are forwarded to Service
    def get_hardware_finish(self):
        self._update_hap_pairings()
        log.info("get_hardware_finish")
        return self.service.get_hardware_finish()

    def get_nfc_access_supported_configuration(self):
        self._update_hap_pairings()
        log.info("get_nfc_access_supported_configuration")
        return self.service.get_nfc_access_supported_configuration()

    def get_nfc_access_control_point(self):
        self._update_hap_pairings()
        log.info("get_nfc_access_control_point")
        return self.service.get_nfc_access_control_point()

    def set_nfc_access_control_point(self, value):
        self._update_hap_pairings()
        log.info(f"set_nfc_access_control_point {value}")
        return self.service.set_nfc_access_control_point(value)

    def get_configuration_state(self):
        self._update_hap_pairings()
        log.info("get_configuration_state")
        return self.service.get_configuration_state()

    @property
    def clients(self):
        return self.driver.state.paired_clients

    def on_unpair(self, client_id):
        log.info(f"on_unpair {client_id}")
        self._update_hap_pairings()

    def __del__(self):
        """Cleanup GPIO when object is destroyed"""
        if self.gpio_pin is not None and GPIO_AVAILABLE:
            try:
                # Note: gpiozero's LED handles cleanup automatically
                # No manual GPIO.output or GPIO.cleanup needed
                log.info(f"GPIO pin {self.gpio_pin} cleaned up")
            except Exception as e:
                log.error(f"Failed to cleanup GPIO pin {self.gpio_pin}: {e}")
