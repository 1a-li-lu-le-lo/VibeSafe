"""
Test suite for encryption functionality
"""
import pytest
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from vibesafe.encryption import EncryptionManager


class TestEncryption:
    @pytest.fixture
    def encryption_manager(self):
        return EncryptionManager()
    
    @pytest.fixture
    def key_pair(self, encryption_manager):
        return encryption_manager.generate_key_pair()
    
    def test_key_generation(self, encryption_manager):
        """Test RSA key pair generation"""
        private_key, public_key = encryption_manager.generate_key_pair()
        
        assert private_key is not None
        assert public_key is not None
        assert private_key.key_size == 2048
    
    def test_encrypt_decrypt_cycle(self, encryption_manager, key_pair):
        """Test full encryption/decryption cycle"""
        private_key, public_key = key_pair
        test_secret = "This is a test secret with special chars: !@#$%^&*()"
        
        # Encrypt
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key)
        
        # Verify encrypted data structure
        assert 'enc_key' in encrypted_data
        assert 'nonce' in encrypted_data
        assert 'ciphertext' in encrypted_data
        assert all(isinstance(v, str) for v in encrypted_data.values())
        
        # Decrypt
        decrypted = encryption_manager.decrypt_secret(encrypted_data, private_key)
        
        assert decrypted == test_secret
    
    def test_encrypt_empty_string(self, encryption_manager, key_pair):
        """Test encrypting empty string"""
        private_key, public_key = key_pair
        test_secret = ""
        
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key)
        decrypted = encryption_manager.decrypt_secret(encrypted_data, private_key)
        
        assert decrypted == test_secret
    
    def test_encrypt_large_secret(self, encryption_manager, key_pair):
        """Test encrypting large secret"""
        private_key, public_key = key_pair
        test_secret = "A" * 10000  # 10KB secret
        
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key)
        decrypted = encryption_manager.decrypt_secret(encrypted_data, private_key)
        
        assert decrypted == test_secret
    
    def test_encrypt_unicode(self, encryption_manager, key_pair):
        """Test encrypting Unicode characters"""
        private_key, public_key = key_pair
        test_secret = "Hello 世界 🔐 Привет"
        
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key)
        decrypted = encryption_manager.decrypt_secret(encrypted_data, private_key)
        
        assert decrypted == test_secret
    
    def test_decrypt_with_wrong_key(self, encryption_manager):
        """Test decryption with wrong private key fails"""
        # Generate two different key pairs
        private_key1, public_key1 = encryption_manager.generate_key_pair()
        private_key2, _ = encryption_manager.generate_key_pair()
        
        test_secret = "Secret message"
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key1)
        
        # Should fail to decrypt with wrong key
        with pytest.raises(Exception):
            encryption_manager.decrypt_secret(encrypted_data, private_key2)
    
    def test_tampered_ciphertext(self, encryption_manager, key_pair):
        """Test that tampered ciphertext fails to decrypt"""
        private_key, public_key = key_pair
        test_secret = "Secret message"
        
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key)
        
        # Tamper with ciphertext
        import base64
        original = base64.b64decode(encrypted_data['ciphertext'])
        tampered = original[:-1] + b'X'  # Change last byte
        encrypted_data['ciphertext'] = base64.b64encode(tampered).decode('utf-8')
        
        # Should fail to decrypt
        with pytest.raises(Exception):
            encryption_manager.decrypt_secret(encrypted_data, private_key)
    
    def test_key_serialization(self, encryption_manager, key_pair):
        """Test key serialization and deserialization"""
        private_key, public_key = key_pair
        
        # Serialize
        private_pem = encryption_manager.serialize_private_key(private_key)
        public_pem = encryption_manager.serialize_public_key(public_key)
        
        assert isinstance(private_pem, bytes)
        assert isinstance(public_pem, bytes)
        assert b'BEGIN RSA PRIVATE KEY' in private_pem or b'BEGIN PRIVATE KEY' in private_pem
        assert b'BEGIN PUBLIC KEY' in public_pem
        
        # Deserialize
        private_key2 = encryption_manager.deserialize_private_key(private_pem)
        public_key2 = encryption_manager.deserialize_public_key(public_pem)
        
        # Test that deserialized keys work
        test_secret = "Test after deserialization"
        encrypted_data = encryption_manager.encrypt_secret(test_secret, public_key2)
        decrypted = encryption_manager.decrypt_secret(encrypted_data, private_key2)
        
        assert decrypted == test_secret