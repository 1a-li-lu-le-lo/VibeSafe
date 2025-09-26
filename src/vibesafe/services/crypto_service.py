"""
Cryptographic Service for VibeSafe

Handles all encryption, decryption, and key management operations.
"""

from typing import Tuple, Dict, Any, Optional
import functools
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from ..encryption import EncryptionManager
from ..exceptions import VibeSafeError


class CryptoService:
    """Service for cryptographic operations with caching and performance optimizations"""

    def __init__(self):
        self.encryption_manager = EncryptionManager()
        self._key_cache = {}

    def generate_key_pair(self) -> Tuple[RSAPrivateKey, RSAPublicKey]:
        """Generate a new RSA key pair"""
        return self.encryption_manager.generate_key_pair()

    def encrypt_secret(self, plaintext: str, public_key: RSAPublicKey) -> Dict[str, Any]:
        """Encrypt a single secret"""
        try:
            return self.encryption_manager.encrypt_secret(plaintext, public_key)
        except Exception as e:
            raise VibeSafeError(f"Encryption failed: {e}")

    def decrypt_secret(self, encrypted_data: Dict[str, Any], private_key: RSAPrivateKey) -> str:
        """Decrypt a single secret"""
        try:
            return self.encryption_manager.decrypt_secret(encrypted_data, private_key)
        except ValueError:
            raise VibeSafeError("Decryption failed: Invalid key or corrupted data")
        except Exception as e:
            raise VibeSafeError(f"Decryption failed: {e}")

    def encrypt_secrets_batch(self, secrets: Dict[str, str], public_key: RSAPublicKey) -> Dict[str, Dict[str, Any]]:
        """Encrypt multiple secrets efficiently

        This is a performance optimization for bulk operations like key rotation.
        """
        encrypted_secrets = {}
        for name, plaintext in secrets.items():
            try:
                encrypted_secrets[name] = self.encrypt_secret(plaintext, public_key)
            except VibeSafeError as e:
                raise VibeSafeError(f"Failed to encrypt secret '{name}': {e}")
        return encrypted_secrets

    def decrypt_secrets_batch(self, encrypted_secrets: Dict[str, Dict[str, Any]], private_key: RSAPrivateKey) -> Dict[str, str]:
        """Decrypt multiple secrets efficiently"""
        decrypted_secrets = {}
        for name, encrypted_data in encrypted_secrets.items():
            try:
                decrypted_secrets[name] = self.decrypt_secret(encrypted_data, private_key)
            except VibeSafeError as e:
                raise VibeSafeError(f"Failed to decrypt secret '{name}': {e}")
        return decrypted_secrets

    def serialize_private_key(self, private_key: RSAPrivateKey, passphrase: Optional[bytes] = None) -> bytes:
        """Serialize private key to PEM format"""
        return EncryptionManager.serialize_private_key(private_key, passphrase)

    def serialize_public_key(self, public_key: RSAPublicKey) -> bytes:
        """Serialize public key to PEM format"""
        return EncryptionManager.serialize_public_key(public_key)

    def deserialize_private_key(self, pem_data: bytes, passphrase: Optional[bytes] = None) -> RSAPrivateKey:
        """Deserialize private key from PEM format"""
        return EncryptionManager.deserialize_private_key(pem_data, passphrase)

    def deserialize_public_key(self, pem_data: bytes) -> RSAPublicKey:
        """Deserialize public key from PEM format"""
        return EncryptionManager.deserialize_public_key(pem_data)

    @functools.lru_cache(maxsize=2)
    def _cache_key(self, key_data: bytes, key_type: str) -> Any:
        """Cache frequently used keys to improve performance"""
        if key_type == 'public':
            return self.deserialize_public_key(key_data)
        elif key_type == 'private':
            return self.deserialize_private_key(key_data)
        else:
            raise ValueError(f"Unknown key type: {key_type}")

    def clear_key_cache(self):
        """Clear cached keys (useful for key rotation)"""
        self._cache_key.cache_clear()
        self._key_cache.clear()