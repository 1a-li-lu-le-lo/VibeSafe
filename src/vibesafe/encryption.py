"""
Encryption module for VibeSafe
Handles RSA + AES-GCM hybrid encryption
"""
import os
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    def __init__(self, key_size=2048):
        self.key_size = key_size
        self.backend = default_backend()
    
    def generate_key_pair(self):
        """Generate a new RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=self.backend
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def encrypt_secret(self, plaintext: str, public_key) -> dict:
        """
        Encrypt a secret using hybrid encryption (RSA + AES-GCM)
        Returns dict with encrypted components
        """
        # Convert plaintext to bytes
        plaintext_bytes = plaintext.encode('utf-8')
        
        # Generate random AES key
        aes_key = AESGCM.generate_key(bit_length=256)
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(aes_key)
        
        # Generate random nonce
        nonce = os.urandom(12)  # 96 bits for GCM
        
        # Encrypt the plaintext
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # Encrypt the AES key with RSA public key
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Return all components as base64-encoded strings
        return {
            'enc_key': base64.b64encode(encrypted_key).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }
    
    def decrypt_secret(self, encrypted_data: dict, private_key) -> str:
        """
        Decrypt a secret using the private key
        """
        # Decode from base64
        encrypted_key = base64.b64decode(encrypted_data['enc_key'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        
        # Decrypt the AES key with RSA private key
        aes_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt the ciphertext with AES-GCM
        aesgcm = AESGCM(aes_key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Convert back to string
        return plaintext_bytes.decode('utf-8')
    
    @staticmethod
    def serialize_private_key(private_key, password=None):
        """Serialize private key to PEM format"""
        if password:
            encryption = serialization.BestAvailableEncryption(password)
        else:
            encryption = serialization.NoEncryption()
        
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )
    
    @staticmethod
    def serialize_public_key(public_key):
        """Serialize public key to PEM format"""
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    @staticmethod
    def deserialize_private_key(pem_data, password=None):
        """Deserialize private key from PEM format"""
        return serialization.load_pem_private_key(
            pem_data,
            password=password,
            backend=default_backend()
        )
    
    @staticmethod
    def deserialize_public_key(pem_data):
        """Deserialize public key from PEM format"""
        return serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )