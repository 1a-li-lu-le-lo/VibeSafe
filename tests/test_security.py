"""
Security-focused test suite
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from vibesafe.storage import StorageManager
from vibesafe.encryption import EncryptionManager
from vibesafe.exceptions import VibeSafeError


class TestSecurity:
    @pytest.mark.security
    def test_file_permissions_unix(self, temp_dir):
        """Test that files are created with secure permissions on Unix"""
        if os.name == 'nt':
            pytest.skip("Unix-only test")
        
        storage = StorageManager(base_dir=temp_dir)
        em = EncryptionManager()
        private_key, public_key = em.generate_key_pair()
        
        # Save keys and check permissions
        storage.save_keys(private_key, public_key)
        
        # Private key should be 600 (owner read/write only)
        priv_mode = oct(storage.priv_key_file.stat().st_mode)[-3:]
        assert priv_mode == '600', f"Private key has insecure permissions: {priv_mode}"
        
        # Directory should be 700 (owner only)
        dir_mode = oct(Path(temp_dir).stat().st_mode)[-3:]
        assert dir_mode == '700', f"Directory has insecure permissions: {dir_mode}"
    
    @pytest.mark.security
    def test_private_key_overwrite_on_delete(self, temp_dir):
        """Test that private key is overwritten before deletion"""
        storage = StorageManager(base_dir=temp_dir)
        em = EncryptionManager()
        private_key, public_key = em.generate_key_pair()
        
        # Save private key
        storage.save_keys(private_key, public_key)
        
        # Get original content
        original_content = storage.priv_key_file.read_bytes()
        original_size = len(original_content)
        
        # Mock the file operations to verify overwrite
        writes = []
        original_open = open
        
        def mock_open(path, mode='r', *args, **kwargs):
            if str(path) == str(storage.priv_key_file) and 'w' in mode:
                # Capture writes to private key file
                file_obj = original_open(path, mode, *args, **kwargs)
                original_write = file_obj.write
                
                def mock_write(data):
                    writes.append(data)
                    return original_write(data)
                
                file_obj.write = mock_write
                return file_obj
            return original_open(path, mode, *args, **kwargs)
        
        with patch('builtins.open', mock_open):
            storage.remove_private_key_file()
        
        # Verify file was overwritten with random data
        assert len(writes) > 0
        assert len(writes[0]) == original_size
        assert writes[0] != original_content  # Should be random
        assert not storage.priv_key_file.exists()
    
    @pytest.mark.security
    def test_no_plaintext_in_storage(self, temp_dir):
        """Test that no plaintext secrets are stored"""
        storage = StorageManager(base_dir=temp_dir)
        
        # Save some encrypted secrets
        test_secrets = {
            "API_KEY": {
                "enc_key": "encrypted_key_data",
                "nonce": "random_nonce",
                "ciphertext": "encrypted_secret"
            }
        }
        storage.save_secrets(test_secrets)
        
        # Read raw file content
        content = storage.secrets_file.read_text()
        
        # These should never appear as actual values in the file
        forbidden_patterns = [
            '"sk-',  # OpenAI key prefix as value
            '"password"',  # password as value
            '"Bearer ',  # Bearer token as value
            '"Basic ',   # Basic auth as value
            'my_secret_password',  # The actual test secret
            'super_secret_token',  # The actual test token
        ]
        
        for forbidden in forbidden_patterns:
            assert forbidden.lower() not in content.lower(), f"Found forbidden pattern: {forbidden}"
    
    @pytest.mark.security
    def test_encryption_randomness(self):
        """Test that encryption produces different ciphertexts for same plaintext"""
        em = EncryptionManager()
        private_key, public_key = em.generate_key_pair()
        
        secret = "same secret value"
        
        # Encrypt same secret multiple times
        encrypted1 = em.encrypt_secret(secret, public_key)
        encrypted2 = em.encrypt_secret(secret, public_key)
        encrypted3 = em.encrypt_secret(secret, public_key)
        
        # All should have different nonces
        assert encrypted1['nonce'] != encrypted2['nonce']
        assert encrypted2['nonce'] != encrypted3['nonce']
        
        # All should have different ciphertexts
        assert encrypted1['ciphertext'] != encrypted2['ciphertext']
        assert encrypted2['ciphertext'] != encrypted3['ciphertext']
        
        # All should have different encrypted keys
        assert encrypted1['enc_key'] != encrypted2['enc_key']
        assert encrypted2['enc_key'] != encrypted3['enc_key']
        
        # But all should decrypt to same value
        assert em.decrypt_secret(encrypted1, private_key) == secret
        assert em.decrypt_secret(encrypted2, private_key) == secret
        assert em.decrypt_secret(encrypted3, private_key) == secret
    
    @pytest.mark.security
    def test_key_strength(self):
        """Test that generated keys meet security requirements"""
        em = EncryptionManager()
        private_key, public_key = em.generate_key_pair()
        
        # Check RSA key size
        assert private_key.key_size >= 2048
        
        # Check that we can specify larger keys
        em_4096 = EncryptionManager(key_size=4096)
        private_key_4096, _ = em_4096.generate_key_pair()
        assert private_key_4096.key_size == 4096
    
    @pytest.mark.security
    def test_timing_attack_resistance(self):
        """Test that decryption failures don't leak timing information"""
        em = EncryptionManager()
        private_key1, public_key1 = em.generate_key_pair()
        private_key2, _ = em.generate_key_pair()
        
        secret = "test secret"
        encrypted = em.encrypt_secret(secret, public_key1)
        
        import time
        
        # Time successful decryption
        start = time.perf_counter()
        try:
            em.decrypt_secret(encrypted, private_key1)
        except:
            pass
        success_time = time.perf_counter() - start
        
        # Time failed decryption
        start = time.perf_counter()
        try:
            em.decrypt_secret(encrypted, private_key2)
        except:
            pass
        fail_time = time.perf_counter() - start
        
        # Times should be reasonably similar (within order of magnitude)
        # This is a basic check - proper timing attack testing requires statistical analysis
        ratio = max(success_time, fail_time) / min(success_time, fail_time)
        assert ratio < 10, "Decryption timing may leak information"