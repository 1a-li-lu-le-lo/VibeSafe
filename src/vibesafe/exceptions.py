"""
Custom exceptions for VibeSafe
"""


class VibeSafeError(Exception):
    """Base exception for VibeSafe"""
    pass


class StorageError(VibeSafeError):
    """Storage-related errors"""
    pass


class EncryptionError(VibeSafeError):
    """Encryption/decryption errors"""
    pass


class PasskeyError(VibeSafeError):
    """Passkey authentication errors"""
    pass


class AuthenticationError(PasskeyError):
    """Authentication failed or was cancelled"""
    pass