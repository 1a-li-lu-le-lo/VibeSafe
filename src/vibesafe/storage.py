"""
Storage module for VibeSafe
Handles file operations with proper permissions
"""
import os
import json
from pathlib import Path
from .encryption import EncryptionManager
from .exceptions import StorageError


class StorageManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = Path.home() / '.vibesafe'
        self.base_dir = Path(base_dir)
        self.priv_key_file = self.base_dir / 'private.pem'
        self.pub_key_file = self.base_dir / 'public.pem'
        self.secrets_file = self.base_dir / 'secrets.json'
        self.config_file = self.base_dir / 'config.json'
        
        # Ensure directory exists with proper permissions
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Create base directory with restricted permissions"""
        self.base_dir.mkdir(mode=0o700, exist_ok=True)
    
    def _set_file_permissions(self, file_path, mode=0o600):
        """Set restrictive file permissions"""
        try:
            os.chmod(file_path, mode)
        except Exception:
            # Non-fatal on Windows
            pass
    
    def key_exists(self):
        """Check if key pair exists"""
        return self.pub_key_file.exists() and (
            self.priv_key_file.exists() or self._passkey_enabled()
        )
    
    def private_key_file_exists(self):
        """Check if private key file exists on disk"""
        return self.priv_key_file.exists()
    
    def _passkey_enabled(self):
        """Check if passkey protection is enabled"""
        config = self.load_config()
        return config.get('passkey_enabled', False)
    
    def save_keys(self, private_key, public_key):
        """Save key pair to files"""
        # Serialize keys
        priv_pem = EncryptionManager.serialize_private_key(private_key)
        pub_pem = EncryptionManager.serialize_public_key(public_key)
        
        # Write private key with restricted permissions
        self.priv_key_file.write_bytes(priv_pem)
        self._set_file_permissions(self.priv_key_file, 0o600)
        
        # Write public key (can be less restrictive)
        self.pub_key_file.write_bytes(pub_pem)
        self._set_file_permissions(self.pub_key_file, 0o644)
    
    def save_private_key(self, private_key):
        """Save only the private key"""
        priv_pem = EncryptionManager.serialize_private_key(private_key)
        self.priv_key_file.write_bytes(priv_pem)
        self._set_file_permissions(self.priv_key_file, 0o600)
    
    def load_private_key(self):
        """Load private key from file"""
        if not self.priv_key_file.exists():
            raise StorageError("Private key file not found")
        
        pem_data = self.priv_key_file.read_bytes()
        return EncryptionManager.deserialize_private_key(pem_data)
    
    def load_public_key(self):
        """Load public key from file"""
        if not self.pub_key_file.exists():
            raise StorageError("Public key file not found")
        
        pem_data = self.pub_key_file.read_bytes()
        return EncryptionManager.deserialize_public_key(pem_data)
    
    def remove_private_key_file(self):
        """Securely remove private key file"""
        if self.priv_key_file.exists():
            # Overwrite with random data before deletion
            size = self.priv_key_file.stat().st_size
            with open(self.priv_key_file, 'wb') as f:
                f.write(os.urandom(size))
            self.priv_key_file.unlink()
    
    def load_secrets(self):
        """Load secrets from JSON file"""
        if not self.secrets_file.exists():
            return {}
        
        try:
            with open(self.secrets_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, IOError):
            raise StorageError("Failed to load secrets file")
        
        return {}
    
    def save_secrets(self, secrets):
        """Save secrets to JSON file"""
        self._ensure_directory()
        
        with open(self.secrets_file, 'w') as f:
            json.dump(secrets, f, indent=2)
        
        self._set_file_permissions(self.secrets_file, 0o600)
    
    def load_config(self):
        """Load configuration"""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def save_config(self, config):
        """Save configuration"""
        self._ensure_directory()
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        self._set_file_permissions(self.config_file, 0o600)