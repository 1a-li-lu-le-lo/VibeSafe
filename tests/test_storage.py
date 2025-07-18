"""
Test suite for storage functionality
"""
import pytest
import tempfile
import shutil
import os
import json
from pathlib import Path
from vibesafe.storage import StorageManager
from vibesafe.encryption import EncryptionManager
from vibesafe.exceptions import StorageError


class TestStorage:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def storage_manager(self, temp_dir):
        """Create storage manager with temp directory"""
        return StorageManager(base_dir=temp_dir)
    
    @pytest.fixture
    def key_pair(self):
        """Generate a test key pair"""
        em = EncryptionManager()
        return em.generate_key_pair()
    
    def test_directory_creation(self, temp_dir):
        """Test that base directory is created with correct permissions"""
        storage = StorageManager(base_dir=temp_dir)
        
        assert Path(temp_dir).exists()
        if os.name != 'nt':  # Skip permission check on Windows
            assert oct(Path(temp_dir).stat().st_mode)[-3:] == '700'
    
    def test_save_and_load_keys(self, storage_manager, key_pair):
        """Test saving and loading key pair"""
        private_key, public_key = key_pair
        
        # Save keys
        storage_manager.save_keys(private_key, public_key)
        
        # Check files exist
        assert storage_manager.priv_key_file.exists()
        assert storage_manager.pub_key_file.exists()
        
        # Check permissions (Unix only)
        if os.name != 'nt':
            assert oct(storage_manager.priv_key_file.stat().st_mode)[-3:] == '600'
            assert oct(storage_manager.pub_key_file.stat().st_mode)[-3:] == '644'
        
        # Load keys
        loaded_private = storage_manager.load_private_key()
        loaded_public = storage_manager.load_public_key()
        
        # Verify they work
        em = EncryptionManager()
        test_data = "Test message"
        encrypted = em.encrypt_secret(test_data, loaded_public)
        decrypted = em.decrypt_secret(encrypted, loaded_private)
        assert decrypted == test_data
    
    def test_key_exists(self, storage_manager, key_pair):
        """Test key existence checking"""
        assert not storage_manager.key_exists()
        
        private_key, public_key = key_pair
        storage_manager.save_keys(private_key, public_key)
        
        assert storage_manager.key_exists()
    
    def test_save_and_load_secrets(self, storage_manager):
        """Test saving and loading secrets"""
        test_secrets = {
            "API_KEY": {"enc_key": "test1", "nonce": "test2", "ciphertext": "test3"},
            "DB_PASS": {"enc_key": "test4", "nonce": "test5", "ciphertext": "test6"}
        }
        
        # Save secrets
        storage_manager.save_secrets(test_secrets)
        
        # Check file exists with correct permissions
        assert storage_manager.secrets_file.exists()
        if os.name != 'nt':
            assert oct(storage_manager.secrets_file.stat().st_mode)[-3:] == '600'
        
        # Load secrets
        loaded = storage_manager.load_secrets()
        assert loaded == test_secrets
    
    def test_load_empty_secrets(self, storage_manager):
        """Test loading when no secrets file exists"""
        secrets = storage_manager.load_secrets()
        assert secrets == {}
    
    def test_remove_private_key(self, storage_manager, key_pair):
        """Test secure removal of private key"""
        private_key, public_key = key_pair
        storage_manager.save_keys(private_key, public_key)
        
        assert storage_manager.priv_key_file.exists()
        
        # Remove private key
        storage_manager.remove_private_key_file()
        
        assert not storage_manager.priv_key_file.exists()
    
    def test_config_operations(self, storage_manager):
        """Test config save and load"""
        test_config = {
            "passkey_enabled": True,
            "passkey_type": "macos"
        }
        
        # Save config
        storage_manager.save_config(test_config)
        
        # Check file exists
        assert storage_manager.config_file.exists()
        if os.name != 'nt':
            assert oct(storage_manager.config_file.stat().st_mode)[-3:] == '600'
        
        # Load config
        loaded = storage_manager.load_config()
        assert loaded == test_config
    
    def test_load_corrupted_secrets(self, storage_manager):
        """Test handling of corrupted secrets file"""
        # Write invalid JSON
        storage_manager.secrets_file.write_text("invalid json{")
        
        with pytest.raises(StorageError):
            storage_manager.load_secrets()
    
    def test_private_key_not_found(self, storage_manager):
        """Test loading non-existent private key"""
        with pytest.raises(StorageError):
            storage_manager.load_private_key()
    
    def test_public_key_not_found(self, storage_manager):
        """Test loading non-existent public key"""
        with pytest.raises(StorageError):
            storage_manager.load_public_key()