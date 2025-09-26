"""
VibeSafe - Secure Secrets Manager with Passkey Protection
"""

__version__ = "1.0.0"
__author__ = "VibeSafe Team"

from .vibesafe import cli, VibeSafe, create_api_client
from .exceptions import VibeSafeError

__all__ = ['cli', 'VibeSafe', 'create_api_client', 'VibeSafeError']