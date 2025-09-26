"""
Secret Service for VibeSafe

Handles business logic for secret management operations.
"""

import re
from typing import Dict, List, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from .crypto_service import CryptoService
from .storage_service import StorageService
from ..exceptions import VibeSafeError


class SecretService:
    """Service for secret management business logic"""

    def __init__(self, storage_service: StorageService, crypto_service: CryptoService):
        self.storage = storage_service
        self.crypto = crypto_service

    def validate_secret_name(self, name: str) -> bool:
        """Validate secret name for security and consistency"""
        if not name or len(name) > 100:
            return False
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))

    def add_secret(self, name: str, value: str, public_key: RSAPublicKey, overwrite: bool = False) -> None:
        """Add a new secret with validation"""
        # Validate inputs
        if not self.validate_secret_name(name):
            raise VibeSafeError(
                f"Invalid secret name '{name}'. "
                "Use only letters, numbers, underscore, and hyphen (max 100 chars)"
            )

        if not value:
            raise VibeSafeError("Secret value cannot be empty")

        # Load existing secrets
        secrets = self.storage.load_secrets()

        # Check for conflicts
        if name in secrets and not overwrite:
            raise VibeSafeError(f"Secret '{name}' already exists. Use overwrite=True to replace it.")

        # Encrypt and store
        encrypted_data = self.crypto.encrypt_secret(value, public_key)
        secrets[name] = encrypted_data
        self.storage.save_secrets(secrets)

    def get_secret(self, name: str, private_key: RSAPrivateKey) -> str:
        """Retrieve and decrypt a secret"""
        secrets = self.storage.load_secrets()

        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")

        encrypted_data = secrets[name]
        return self.crypto.decrypt_secret(encrypted_data, private_key)

    def delete_secret(self, name: str) -> None:
        """Delete a secret"""
        secrets = self.storage.load_secrets()

        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")

        del secrets[name]
        self.storage.save_secrets(secrets)

    def list_secret_names(self) -> List[str]:
        """Get list of all secret names"""
        secrets = self.storage.load_secrets()
        return sorted(list(secrets.keys()))

    def secret_exists(self, name: str) -> bool:
        """Check if a secret exists"""
        secrets = self.storage.load_secrets()
        return name in secrets

    def get_secrets_count(self) -> int:
        """Get total number of secrets"""
        secrets = self.storage.load_secrets()
        return len(secrets)

    def rotate_secrets(self, old_private_key: RSAPrivateKey, new_public_key: RSAPublicKey) -> Tuple[int, int]:
        """Rotate all secrets to use new encryption keys

        Returns:
            Tuple of (total_secrets, successfully_rotated)
        """
        secrets = self.storage.load_secrets()
        total_secrets = len(secrets)

        if total_secrets == 0:
            return 0, 0

        # Decrypt all secrets with old key
        decrypted_secrets = {}
        failed_decryptions = []

        for name, encrypted_data in secrets.items():
            try:
                plaintext = self.crypto.decrypt_secret(encrypted_data, old_private_key)
                decrypted_secrets[name] = plaintext
            except Exception as e:
                failed_decryptions.append((name, str(e)))

        if failed_decryptions:
            error_details = "; ".join([f"{name}: {error}" for name, error in failed_decryptions])
            raise VibeSafeError(f"Failed to decrypt secrets during rotation: {error_details}")

        # Re-encrypt with new key using batch operation for performance
        new_encrypted_secrets = self.crypto.encrypt_secrets_batch(decrypted_secrets, new_public_key)

        # Clear plaintext from memory
        for key in decrypted_secrets:
            decrypted_secrets[key] = None
        decrypted_secrets.clear()

        # Save new encrypted secrets
        self.storage.save_secrets(new_encrypted_secrets)

        return total_secrets, len(new_encrypted_secrets)

    def export_secrets(self, include_metadata: bool = True) -> Dict:
        """Export secrets in a structured format"""
        secrets = self.storage.load_secrets()
        config = self.storage.load_config()

        export_data = {
            'version': '1.0.0',
            'secrets': secrets,
        }

        if include_metadata:
            export_data['metadata'] = {
                'secret_count': len(secrets),
                'secret_names': sorted(secrets.keys()),
                'config': config
            }

        return export_data

    def import_secrets(self, import_data: Dict, overwrite: bool = False) -> Tuple[int, int]:
        """Import secrets from export data

        Returns:
            Tuple of (total_imported, skipped_existing)
        """
        if not isinstance(import_data, dict):
            raise VibeSafeError("Invalid import data format")

        if 'secrets' not in import_data:
            raise VibeSafeError("No secrets found in import data")

        imported_secrets = import_data['secrets']
        if not isinstance(imported_secrets, dict):
            raise VibeSafeError("Invalid secrets format in import data")

        current_secrets = self.storage.load_secrets()
        total_imported = 0
        skipped_existing = 0

        for name, encrypted_data in imported_secrets.items():
            if name in current_secrets and not overwrite:
                skipped_existing += 1
                continue

            # Validate secret name
            if not self.validate_secret_name(name):
                raise VibeSafeError(f"Invalid secret name in import data: '{name}'")

            current_secrets[name] = encrypted_data
            total_imported += 1

        self.storage.save_secrets(current_secrets)
        return total_imported, skipped_existing

    def search_secrets(self, query: str) -> List[str]:
        """Search secret names by pattern"""
        if not query:
            return self.list_secret_names()

        secret_names = self.list_secret_names()
        query_lower = query.lower()

        # Simple substring search
        matching_names = [
            name for name in secret_names
            if query_lower in name.lower()
        ]

        return sorted(matching_names)

    def get_secret_info(self, name: str) -> Dict:
        """Get metadata about a specific secret"""
        secrets = self.storage.load_secrets()

        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")

        encrypted_data = secrets[name]
        return {
            'name': name,
            'exists': True,
            'encrypted_size': len(str(encrypted_data)) if encrypted_data else 0,
            # Don't include actual encrypted data for security
        }