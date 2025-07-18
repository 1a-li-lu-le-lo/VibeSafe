"""
macOS Keychain integration for VibeSafe
Uses Touch ID / Face ID for authentication
"""
import platform
from .exceptions import PasskeyError, AuthenticationError

# Only import macOS-specific modules if on Darwin
if platform.system() != 'Darwin':
    raise ImportError("This module is only for macOS")

try:
    import objc
    import Security
    import LocalAuthentication
    from Foundation import NSData, NSString
except ImportError:
    raise ImportError("pyobjc is required for macOS passkey support")

from .encryption import EncryptionManager


SERVICE = "com.vibesafe.private-key"
ACCOUNT = "default"


class MacPasskeyManager:
    def __init__(self):
        self.storage = None  # Will be set by main VibeSafe class if needed
    
    def _create_access_control(self, flags=Security.kSecAccessControlUserPresence):
        """Create an access control object requiring biometric authentication"""
        access_control = Security.SecAccessControlCreateWithFlags(
            None,  # allocator
            Security.kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
            flags,
            None  # error pointer
        )
        if not access_control:
            raise PasskeyError("Failed to create access control")
        return access_control
    
    def store_private_key(self, private_key):
        """Store private key in macOS Keychain with biometric protection"""
        # Serialize the private key
        pem_data = EncryptionManager.serialize_private_key(private_key)
        
        # Create NSData properly
        try:
            ns_data = NSData.dataWithBytes_length_(pem_data, len(pem_data))
        except Exception:
            # Fallback: create NSData differently
            from Foundation import NSData
            ns_data = NSData.alloc().initWithBytes_length_(pem_data, len(pem_data))
        
        # Create access control requiring biometric authentication
        access_control = Security.SecAccessControlCreateWithFlags(
            None,  # allocator
            Security.kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            Security.kSecAccessControlBiometryAny,
            None  # error pointer
        )
        
        if not access_control:
            raise PasskeyError("Failed to create access control for biometric authentication")
        
        # Store in Keychain with biometric protection
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: SERVICE,
            Security.kSecAttrAccount: ACCOUNT,
            Security.kSecValueData: ns_data,
            Security.kSecAttrAccessible: Security.kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        }
        
        # Delete any existing item first
        delete_query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: SERVICE,
            Security.kSecAttrAccount: ACCOUNT,
        }
        Security.SecItemDelete(delete_query)
        
        # Add the new item
        status = Security.SecItemAdd(query, None)
        
        # Handle tuple return (status, item) or just status
        if isinstance(status, tuple):
            actual_status = status[0]
        else:
            actual_status = status
            
        if actual_status != 0:
            raise PasskeyError(f"Failed to store key in Keychain: {actual_status}")
        
        # Update config to mark passkey as enabled
        if hasattr(self, 'storage') and self.storage:
            config = self.storage.load_config()
            config['passkey_enabled'] = True
            self.storage.save_config(config)
    
    def retrieve_private_key(self):
        """Retrieve private key from Keychain with biometric authentication"""
        # Try to set process name to VibeSafe for better branding in Touch ID prompt
        try:
            import sys
            import os
            from Foundation import NSBundle, NSProcessInfo
            
            # Try to set the process name
            process_info = NSProcessInfo.processInfo()
            process_info.setProcessName_("VibeSafe")
            
            # Try to set bundle identifier if possible
            bundle = NSBundle.mainBundle()
            if bundle:
                bundle_info = bundle.infoDictionary()
                if bundle_info:
                    bundle_info.setObject_forKey_("VibeSafe", "CFBundleName")
                    bundle_info.setObject_forKey_("com.vibesafe.cli", "CFBundleIdentifier")
        except Exception:
            # If setting process name fails, continue anyway
            pass
        
        # First check if biometric authentication is available
        context = LocalAuthentication.LAContext.alloc().init()
        
        # Try to customize the authentication context for VibeSafe branding
        context.setLocalizedFallbackTitle_("Use VibeSafe Passcode")
        context.setLocalizedCancelTitle_("Cancel VibeSafe")
        
        # Check if biometric authentication is available
        can_evaluate = context.canEvaluatePolicy_error_(
            LocalAuthentication.LAPolicyDeviceOwnerAuthenticationWithBiometrics,
            None
        )
        
        if not can_evaluate:
            raise PasskeyError("Biometric authentication not available. Please enable Touch ID or Face ID.")
        
        # Perform biometric authentication first
        import time
        import threading
        
        auth_result = {'success': False, 'error': None, 'completed': False}
        
        def auth_callback(success, error):
            auth_result['success'] = success
            auth_result['error'] = error
            auth_result['completed'] = True
        
        # Start authentication with custom reason that includes VibeSafe branding
        context.evaluatePolicy_localizedReason_reply_(
            LocalAuthentication.LAPolicyDeviceOwnerAuthenticationWithBiometrics,
            "VibeSafe CLI wants to access your encrypted secrets",
            auth_callback
        )
        
        # Wait for authentication to complete
        timeout = 30.0  # 30 second timeout
        start_time = time.time()
        
        while not auth_result['completed']:
            if time.time() - start_time > timeout:
                raise PasskeyError("Authentication timed out")
            time.sleep(0.1)
        
        if not auth_result['success']:
            error_msg = str(auth_result['error']) if auth_result['error'] else "Authentication failed"
            raise PasskeyError(f"Biometric authentication failed: {error_msg}")
        
        # Now retrieve the key from Keychain
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: SERVICE,
            Security.kSecAttrAccount: ACCOUNT,
            Security.kSecReturnData: True,
            Security.kSecMatchLimit: Security.kSecMatchLimitOne,
        }
        
        result = Security.SecItemCopyMatching(query, None)
        
        # Handle different return types
        if isinstance(result, tuple):
            status, data = result
            if status != 0:
                raise PasskeyError(f"Failed to retrieve key from Keychain: {status}")
            actual_result = data
        else:
            # Single return value should be the data
            actual_result = result
        
        if actual_result is None:
            raise PasskeyError("No passkey-protected key found in Keychain")
        
        # Convert NSData to bytes - try multiple methods
        pem_data = None
        
        # Method 1: Direct bytes() conversion
        try:
            pem_data = bytes(actual_result)
            if pem_data and len(pem_data) > 0:
                pass  # Success
            else:
                pem_data = None
        except (TypeError, ValueError):
            pem_data = None
        
        # Method 2: Try PyObjC NSData methods
        if pem_data is None or len(pem_data) == 0:
            try:
                # Try getting bytes through NSData methods
                if hasattr(actual_result, 'bytes'):
                    byte_ptr = actual_result.bytes()
                    length = actual_result.length()
                    pem_data = byte_ptr[:length] if length > 0 else None
                elif hasattr(actual_result, 'getBytes_length_'):
                    length = actual_result.length()
                    if length > 0:
                        import ctypes
                        buffer = (ctypes.c_char * length)()
                        actual_result.getBytes_length_(buffer, length)
                        pem_data = bytes(buffer)
            except (AttributeError, TypeError):
                pass
        
        # Method 3: String conversion fallback
        if pem_data is None or len(pem_data) == 0:
            try:
                pem_string = str(actual_result)
                if pem_string and '-----BEGIN' in pem_string:
                    pem_data = pem_string.encode('utf-8')
            except (TypeError, UnicodeEncodeError):
                pass
        
        # Validate we got valid PEM data
        if not pem_data or len(pem_data) == 0:
            raise PasskeyError("Empty data retrieved from Keychain")
        
        if not pem_data.startswith(b'-----BEGIN'):
            raise PasskeyError(f"Invalid PEM data retrieved from Keychain (length: {len(pem_data)}): {pem_data[:50]}...")
        
        # Deserialize the private key
        return EncryptionManager.deserialize_private_key(pem_data)
    
    def remove_private_key(self):
        """Remove private key from Keychain"""
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: SERVICE,
            Security.kSecAttrAccount: ACCOUNT,
        }
        
        status = Security.SecItemDelete(query)
        
        if status != 0 and status != -25300:  # -25300 = item not found
            raise PasskeyError(f"Failed to remove key from Keychain: {status}")
        
        # Update config
        if hasattr(self, 'storage') and self.storage:
            config = self.storage.load_config()
            config['passkey_enabled'] = False
            self.storage.save_config(config)
    
    def is_enabled(self):
        """Check if passkey protection is enabled"""
        # Check if key exists in Keychain AND config shows it's enabled
        if hasattr(self, 'storage') and self.storage:
            config = self.storage.load_config()
            if not config.get('passkey_enabled', False):
                return False
        
        # Also check if key actually exists in Keychain
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: SERVICE,
            Security.kSecAttrAccount: ACCOUNT,
            Security.kSecReturnAttributes: True,
            Security.kSecMatchLimit: Security.kSecMatchLimitOne,
        }
        
        result = Security.SecItemCopyMatching(query, None)
        return result is not None
    
    def test_authentication(self):
        """Test if biometric authentication is available"""
        try:
            context = LocalAuthentication.LAContext.alloc().init()
            
            # Test for biometric authentication
            can_evaluate = context.canEvaluatePolicy_error_(
                LocalAuthentication.LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                None
            )
            
            if can_evaluate:
                return True
            
            # Try with passcode fallback
            can_evaluate = context.canEvaluatePolicy_error_(
                LocalAuthentication.LAPolicyDeviceOwnerAuthentication,
                None
            )
            
            return can_evaluate
        except Exception:
            return False