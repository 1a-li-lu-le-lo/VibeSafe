"""
Storage Service for VibeSafe

Handles all file operations, atomic writes, and data persistence.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

from ..storage import StorageManager
from ..exceptions import StorageError


class StorageService:
    """Enhanced storage service with better error handling and atomic operations"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.storage_manager = StorageManager(base_dir)

    @property
    def base_dir(self) -> Path:
        return self.storage_manager.base_dir

    @property
    def priv_key_file(self) -> Path:
        return self.storage_manager.priv_key_file

    @property
    def pub_key_file(self) -> Path:
        return self.storage_manager.pub_key_file

    @property
    def secrets_file(self) -> Path:
        return self.storage_manager.secrets_file

    @property
    def config_file(self) -> Path:
        return self.storage_manager.config_file

    def key_exists(self) -> bool:
        """Check if key pair exists"""
        return self.storage_manager.key_exists()

    def private_key_file_exists(self) -> bool:
        """Check if private key file exists on disk"""
        return self.storage_manager.private_key_file_exists()

    @contextmanager
    def atomic_write(self, file_path: Path, mode: int = 0o600):
        """Context manager for atomic file writes with proper cleanup"""
        temp_fd = None
        temp_path = None
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(self.base_dir),
                suffix='.tmp'
            )
            yield temp_fd, temp_path

            # Set permissions and replace atomically
            self.storage_manager._set_file_permissions(temp_path, mode)
            os.replace(temp_path, file_path)
            temp_path = None  # Successfully moved, don't clean up

        except Exception as e:
            # Clean up temp file on error
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise StorageError(f"Atomic write failed: {e}")

    def save_json_data(self, file_path: Path, data: Dict[str, Any], mode: int = 0o600) -> None:
        """Save JSON data atomically"""
        with self.atomic_write(file_path, mode) as (temp_fd, temp_path):
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f, indent=2)

    def load_json_data(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data with error handling"""
        if not file_path.exists():
            return {}

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    raise StorageError(f"Invalid JSON structure in {file_path}")
        except (json.JSONDecodeError, IOError) as e:
            raise StorageError(f"Failed to load {file_path}: {e}")

    def save_binary_data(self, file_path: Path, data: bytes, mode: int = 0o600) -> None:
        """Save binary data atomically"""
        with self.atomic_write(file_path, mode) as (temp_fd, temp_path):
            os.write(temp_fd, data)

    def load_binary_data(self, file_path: Path) -> bytes:
        """Load binary data with error handling"""
        if not file_path.exists():
            raise StorageError(f"File not found: {file_path}")

        try:
            return file_path.read_bytes()
        except IOError as e:
            raise StorageError(f"Failed to read {file_path}: {e}")

    def save_secrets(self, secrets: Dict[str, Any]) -> None:
        """Save secrets with enhanced error handling"""
        if not isinstance(secrets, dict):
            raise StorageError("Secrets must be a dictionary")

        self.save_json_data(self.secrets_file, secrets)

    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets with validation"""
        return self.load_json_data(self.secrets_file)

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration"""
        if not isinstance(config, dict):
            raise StorageError("Config must be a dictionary")

        self.save_json_data(self.config_file, config)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        return self.load_json_data(self.config_file)

    def securely_delete_file(self, file_path: Path) -> None:
        """Securely delete a file by overwriting with random data"""
        if not file_path.exists():
            return

        try:
            # Overwrite with random data before deletion
            size = file_path.stat().st_size
            with open(file_path, 'wb') as f:
                f.write(os.urandom(size))
            file_path.unlink()
        except (OSError, IOError) as e:
            raise StorageError(f"Failed to securely delete {file_path}: {e}")

    def create_backup_directory(self, name: str) -> Path:
        """Create a timestamped backup directory"""
        import datetime

        backup_base = self.base_dir / 'backups'
        backup_base.mkdir(mode=0o700, exist_ok=True)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = backup_base / f"{name}_{timestamp}"
        backup_dir.mkdir(mode=0o700, exist_ok=True)

        return backup_dir

    def get_file_permissions_status(self) -> Dict[str, Any]:
        """Get detailed file permission status for security audit"""
        status = {
            'directory': {
                'path': str(self.base_dir),
                'exists': self.base_dir.exists(),
                'permissions': None,
                'secure': False
            },
            'files': {}
        }

        # Check directory
        if self.base_dir.exists():
            dir_stat = os.stat(self.base_dir)
            dir_mode = dir_stat.st_mode & 0o777
            status['directory']['permissions'] = oct(dir_mode)
            status['directory']['secure'] = dir_mode == 0o700

        # Check key files
        for name, path in [
            ('private_key', self.priv_key_file),
            ('public_key', self.pub_key_file),
            ('secrets', self.secrets_file),
            ('config', self.config_file)
        ]:
            file_status = {
                'path': str(path),
                'exists': path.exists(),
                'permissions': None,
                'secure': False
            }

            if path.exists():
                file_stat = os.stat(path)
                file_mode = file_stat.st_mode & 0o777
                file_status['permissions'] = oct(file_mode)
                # Most files should be 600, public key can be 644
                expected_mode = 0o644 if name == 'public_key' else 0o600
                file_status['secure'] = file_mode == expected_mode

            status['files'][name] = file_status

        return status