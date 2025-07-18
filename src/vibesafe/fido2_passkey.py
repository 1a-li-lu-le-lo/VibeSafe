"""
FIDO2/WebAuthn passkey integration for cross-platform support
"""
import os
import json
import base64
from pathlib import Path

try:
    from fido2.client import Fido2Client, WindowsClient
    from fido2.server import Fido2Server
    from fido2.ctap2 import CTAP2, AttestationObject, AuthenticatorData
    from fido2.cose import ES256
    from fido2.hid import CtapHidDevice
    from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    raise ImportError("fido2 package is required for FIDO2 passkey support")

from .encryption import EncryptionManager
from .exceptions import PasskeyError, AuthenticationError


class Fido2PasskeyManager:
    def __init__(self):
        self.rp_id = "vibesafe.local"
        self.rp_name = "VibeSafe Secrets Manager"
        self.user_id = b"vibesafe-user"
        self.user_name = "vibesafe"
        self.user_display_name = "VibeSafe User"
        
        # Storage paths
        self.base_dir = Path.home() / '.vibesafe'
        self.fido2_dir = self.base_dir / 'fido2'
        self.credential_file = self.fido2_dir / 'credential.json'
        self.wrapped_key_file = self.fido2_dir / 'wrapped_private_key.enc'
        
        # Ensure directories exist
        self.fido2_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        
        # Initialize FIDO2 server
        self.server = Fido2Server(
            PublicKeyCredentialRpEntity(self.rp_id, self.rp_name)
        )
    
    def _get_authenticator(self):
        """Get the first available FIDO2 authenticator"""
        # Try Windows Hello first if on Windows
        if hasattr(WindowsClient, 'is_available') and WindowsClient.is_available():
            return WindowsClient()
        
        # Otherwise look for USB/NFC authenticators
        devices = list(CtapHidDevice.list_devices())
        if not devices:
            raise PasskeyError("No FIDO2 authenticator found")
        
        return Fido2Client(devices[0], self.rp_id)
    
    def register_passkey(self):
        """Register a new FIDO2 passkey"""
        client = self._get_authenticator()
        
        # Create credential
        user = PublicKeyCredentialUserEntity(
            self.user_id,
            self.user_name,
            display_name=self.user_display_name
        )
        
        # Get registration data from server
        create_options, state = self.server.register_begin(
            user,
            user_verification="preferred",
            authenticator_attachment="platform"
        )
        
        # Perform registration with authenticator
        print("Touch your authenticator to register...")
        result = client.make_credential(create_options["publicKey"])
        
        # Complete registration
        auth_data = self.server.register_complete(
            state,
            result.client_data,
            result.attestation_object
        )
        
        # Store credential info
        credential_data = {
            "credential_id": base64.b64encode(auth_data.credential_data.credential_id).decode(),
            "public_key": base64.b64encode(auth_data.credential_data.public_key).decode(),
            "aaguid": base64.b64encode(auth_data.credential_data.aaguid).decode()
        }
        
        with open(self.credential_file, 'w') as f:
            json.dump(credential_data, f, indent=2)
        
        os.chmod(self.credential_file, 0o600)
        
        return credential_data
    
    def _derive_key_from_assertion(self, assertion_response):
        """Derive an AES key from FIDO2 assertion response"""
        # Use the signature as key material
        signature = assertion_response.signature
        
        # Derive a 256-bit key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'vibesafe-fido2-salt',  # Fixed salt for deterministic key
            iterations=100000,
        )
        return kdf.derive(signature[:32])  # Use first 32 bytes of signature
    
    def store_private_key(self, private_key):
        """Wrap and store private key using FIDO2 passkey"""
        # First register if not already done
        if not self.credential_file.exists():
            self.register_passkey()
        
        # Load credential
        with open(self.credential_file, 'r') as f:
            credential_data = json.load(f)
        
        credential_id = base64.b64decode(credential_data["credential_id"])
        
        # Get authenticator
        client = self._get_authenticator()
        
        # Create assertion to get key material
        request_options, state = self.server.authenticate_begin(
            [{"id": credential_id, "type": "public-key"}],
            user_verification="preferred"
        )
        
        print("Touch your authenticator to protect the private key...")
        assertion = client.get_assertion(request_options["publicKey"])
        assertion_response = assertion.get_response(0)
        
        # Derive wrapping key from assertion
        wrapping_key = self._derive_key_from_assertion(assertion_response)
        
        # Serialize private key
        pem_data = EncryptionManager.serialize_private_key(private_key)
        
        # Encrypt private key with derived key
        aesgcm = AESGCM(wrapping_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, pem_data, None)
        
        # Store wrapped key
        wrapped_data = {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode()
        }
        
        with open(self.wrapped_key_file, 'w') as f:
            json.dump(wrapped_data, f, indent=2)
        
        os.chmod(self.wrapped_key_file, 0o600)
        
        # Update config
        config_file = self.base_dir / 'config.json'
        config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        config['passkey_enabled'] = True
        config['passkey_type'] = 'fido2'
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def retrieve_private_key(self):
        """Retrieve and unwrap private key using FIDO2 passkey"""
        if not self.wrapped_key_file.exists():
            raise PasskeyError("No wrapped private key found")
        
        # Load wrapped key
        with open(self.wrapped_key_file, 'r') as f:
            wrapped_data = json.load(f)
        
        # Load credential
        with open(self.credential_file, 'r') as f:
            credential_data = json.load(f)
        
        credential_id = base64.b64decode(credential_data["credential_id"])
        
        # Get authenticator
        client = self._get_authenticator()
        
        # Create assertion to get key material
        request_options, state = self.server.authenticate_begin(
            [{"id": credential_id, "type": "public-key"}],
            user_verification="preferred"
        )
        
        print("Touch your authenticator to access secrets...")
        try:
            assertion = client.get_assertion(request_options["publicKey"])
            assertion_response = assertion.get_response(0)
        except Exception as e:
            if "cancelled" in str(e).lower():
                raise AuthenticationError("Authentication cancelled by user")
            raise PasskeyError(f"FIDO2 authentication failed: {e}")
        
        # Derive unwrapping key from assertion
        unwrapping_key = self._derive_key_from_assertion(assertion_response)
        
        # Decrypt private key
        nonce = base64.b64decode(wrapped_data["nonce"])
        ciphertext = base64.b64decode(wrapped_data["ciphertext"])
        
        aesgcm = AESGCM(unwrapping_key)
        try:
            pem_data = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            raise PasskeyError("Failed to decrypt private key - authentication may have changed")
        
        # Deserialize private key
        return EncryptionManager.deserialize_private_key(pem_data)
    
    def remove_private_key(self):
        """Remove wrapped private key"""
        if self.wrapped_key_file.exists():
            # Overwrite before deletion
            size = self.wrapped_key_file.stat().st_size
            with open(self.wrapped_key_file, 'wb') as f:
                f.write(os.urandom(size))
            self.wrapped_key_file.unlink()
        
        # Update config
        config_file = self.base_dir / 'config.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            config['passkey_enabled'] = False
            config.pop('passkey_type', None)
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
    
    def is_enabled(self):
        """Check if FIDO2 passkey protection is enabled"""
        return self.wrapped_key_file.exists() and self.credential_file.exists()