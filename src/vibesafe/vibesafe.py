#!/usr/bin/env python3
"""
VibeSafe - Secure Secrets Manager CLI with Passkey Protection
"""
import os
import sys
import json
import base64
import platform
import tarfile
import datetime
import stat
import re
from pathlib import Path
from getpass import getpass

import click
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from .encryption import EncryptionManager
from .storage import StorageManager
from .exceptions import VibeSafeError, PasskeyError


def create_api_client():
    """Create a VibeSafe instance optimized for programmatic API usage.

    This creates a non-interactive instance that suppresses CLI prompts
    and is suitable for use in scripts, automation, and AI tool integration.

    Returns:
        VibeSafe: A non-interactive VibeSafe instance

    Example:
        >>> from vibesafe import create_api_client
        >>> vs = create_api_client()
        >>> secret = vs.fetch_secret("API_KEY")
        >>> vs.store_secret("NEW_KEY", "value123")
    """
    return VibeSafe(interactive=False)

# Check if running on macOS for passkey support
IS_MACOS = platform.system() == 'Darwin'
if IS_MACOS:
    try:
        from .mac_passkey import MacPasskeyManager
        PASSKEY_AVAILABLE = True
    except ImportError:
        PASSKEY_AVAILABLE = False
    
    # Removed unused passkey implementations
else:
    PASSKEY_AVAILABLE = False

# Try to import FIDO2 for cross-platform support
try:
    from .fido2_passkey import Fido2PasskeyManager
    FIDO2_AVAILABLE = True
except ImportError:
    FIDO2_AVAILABLE = False


class VibeSafe:
    """VibeSafe - Secure Secrets Manager

    This class provides both CLI and programmatic interfaces for secure secret management.
    The programmatic API methods (fetch_secret, store_secret, etc.) can be used for
    integration with external tools and AI assistants without exposing secrets to stdout.
    """
    def __init__(self, passkey_type=None, interactive=True):
        """Initialize VibeSafe

        Args:
            passkey_type: Optional passkey type override ('keychain' or 'fido2')
            interactive: Whether to show prompts and messages (False for API usage)
        """
        self.storage = StorageManager()
        self.encryption = EncryptionManager()
        self.interactive = interactive

        # Initialize passkey manager based on preference or availability
        self.passkey_manager = None

        if passkey_type == 'fido2' and FIDO2_AVAILABLE:
            self.passkey_manager = Fido2PasskeyManager()
        elif passkey_type == 'keychain' and IS_MACOS and PASSKEY_AVAILABLE:
            self.passkey_manager = MacPasskeyManager()
            self.passkey_manager.storage = self.storage
        elif IS_MACOS and PASSKEY_AVAILABLE and passkey_type is None:
            # Default to keychain on macOS if no preference
            self.passkey_manager = MacPasskeyManager()
            self.passkey_manager.storage = self.storage
        elif FIDO2_AVAILABLE and passkey_type is None:
            self.passkey_manager = Fido2PasskeyManager()
    
    def init_keys(self, use_passphrase=False, passphrase=None):
        """Initialize a new RSA key pair

        Args:
            use_passphrase: Whether to encrypt the private key with a passphrase
            passphrase: The passphrase to use (will prompt if None and use_passphrase is True)
        """
        if self.storage.key_exists():
            raise VibeSafeError("Key pair already exists. Use --force to regenerate.")

        click.echo("Generating new RSA key pair...")
        private_key, public_key = self.encryption.generate_key_pair()

        # Optionally encrypt private key with passphrase
        if use_passphrase:
            if passphrase is None:
                passphrase = getpass("Enter passphrase to protect private key: ")
                passphrase_confirm = getpass("Confirm passphrase: ")
                if passphrase != passphrase_confirm:
                    raise VibeSafeError("Passphrases do not match")
                if len(passphrase) < 8:
                    raise VibeSafeError("Passphrase must be at least 8 characters")

            # Save with passphrase encryption
            self.storage.save_keys_with_passphrase(private_key, public_key, passphrase.encode())
            config = self.storage.load_config()
            config['key_encrypted'] = True
            self.storage.save_config(config)
            click.secho("🔐 Private key encrypted with passphrase", fg='green')
        else:
            self.storage.save_keys(private_key, public_key)

        click.echo(f"✓ Public key saved to:  {self.storage.pub_key_file}")
        click.echo(f"✓ Private key saved to: {self.storage.priv_key_file}")
        click.echo("\n⚠️  Keep your private key safe! If lost, you cannot decrypt existing secrets.")
    
    def add_secret(self, name, value=None, overwrite=False):
        """Add a new secret"""
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")

        # Validate secret name
        if not self._validate_secret_name(name):
            raise VibeSafeError(
                f"Invalid secret name '{name}'. "
                "Use only letters, numbers, underscore, and hyphen (max 100 chars)"
            )

        # Block CLI argument secrets completely (security critical)
        if value is not None and self.interactive:
            raise VibeSafeError(
                "❌ Secret values cannot be passed as command arguments for security.\n"
                "   This prevents exposure in process lists and shell history.\n"
                "   💡 Omit the value to be prompted securely, or use the programmatic API."
            )

        # Get secret value if not provided
        if value is None:
            try:
                value = getpass(f"Enter secret value for '{name}': ")
            except KeyboardInterrupt:
                raise VibeSafeError("\nOperation cancelled.")

        # Check if secret already exists
        secrets = self.storage.load_secrets()
        if name in secrets and not overwrite:
            raise VibeSafeError(f"Secret '{name}' already exists. Use --overwrite to replace it.")
        
        # Load public key and encrypt
        public_key = self.storage.load_public_key()
        encrypted_data = self.encryption.encrypt_secret(value, public_key)
        
        # Save encrypted secret
        secrets[name] = encrypted_data
        self.storage.save_secrets(secrets)
        
        if self.interactive:
            click.echo(f"✓ Secret '{name}' has been added and encrypted.")
    
    def get_secret(self, name, return_value=False):
        """Retrieve and decrypt a secret

        Args:
            name: The name of the secret to retrieve
            return_value: If True, return the plaintext instead of writing to stdout (for internal use)
        """
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")

        secrets = self.storage.load_secrets()
        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")

        # Load private key (may trigger passkey authentication)
        # Use silent mode for programmatic API calls
        # Check for passphrase-encrypted keys
        config = self.storage.load_config()
        passphrase = None
        if config.get('key_encrypted', False) and not (self.passkey_manager and self.passkey_manager.is_enabled()):
            passphrase = self._prompt_for_passphrase()
            if passphrase:
                passphrase = passphrase.encode()

        private_key = self._load_private_key_with_auth(silent=return_value, passphrase=passphrase)

        # Decrypt secret
        encrypted_data = secrets[name]
        try:
            plaintext = self.encryption.decrypt_secret(encrypted_data, private_key)

            # Either return the value (for internal use) or write to stdout (for CLI use)
            if return_value:
                # Clear from memory as soon as possible
                result = plaintext
                plaintext = None
                return result
            else:
                # Check if output is going to terminal (potential security risk)
                if sys.stdout.isatty() and self.interactive:
                    click.secho("⚠️  Warning: This will display your secret on screen!", fg='yellow', err=True)
                    if not click.confirm("Continue?", default=False):
                        raise VibeSafeError("Secret retrieval cancelled for security")

                # Write directly to stdout buffer to avoid encoding issues
                # This ensures the secret goes directly to the destination without being visible
                sys.stdout.buffer.write(plaintext.encode('utf-8'))
                # Clear from memory
                plaintext = None
        except ValueError as e:
            # ValueError typically means wrong key or corrupted data
            raise VibeSafeError(f"Failed to decrypt secret '{name}'. The data may be corrupted or the key may be wrong.")
        except KeyError as e:
            # KeyError means the encrypted data structure is malformed
            raise VibeSafeError(f"Secret '{name}' has invalid format. The data may be corrupted.")
        except Exception as e:
            # Catch-all for other errors, but log the type for debugging
            import logging
            logging.debug(f"Decryption error type: {type(e).__name__}")
            raise VibeSafeError(f"Failed to decrypt secret '{name}'. Please check your authentication.")
    
    def list_secrets(self):
        """List all stored secret names"""
        secrets = self.storage.load_secrets()
        if not secrets:
            click.echo("No secrets stored.")
            return
        
        click.echo("Stored secrets:")
        for name in sorted(secrets.keys()):
            click.echo(f"  • {name}")
    
    def delete_secret(self, name, yes=False):
        """Delete a secret"""
        secrets = self.storage.load_secrets()
        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")
        
        if not yes:
            if not click.confirm(f"Are you sure you want to delete secret '{name}'?"):
                click.echo("Deletion cancelled.")
                return
        
        del secrets[name]
        self.storage.save_secrets(secrets)
        click.echo(f"✓ Secret '{name}' has been deleted.")
    
    def enable_passkey(self, passkey_type=None):
        """Enable passkey protection

        Args:
            passkey_type: Optional passkey type to enable ('keychain' or 'fido2')
        """
        if not self.passkey_manager:
            # Try to initialize with specified type
            if passkey_type == 'fido2' and FIDO2_AVAILABLE:
                self.passkey_manager = Fido2PasskeyManager()
            elif passkey_type == 'keychain' and IS_MACOS and PASSKEY_AVAILABLE:
                self.passkey_manager = MacPasskeyManager()
                self.passkey_manager.storage = self.storage
            else:
                raise VibeSafeError("Passkey support not available on this platform.")

        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")

        # Load existing private key
        private_key = self.storage.load_private_key()

        # Store in secure storage (Keychain on macOS, encrypted with FIDO2 elsewhere)
        click.secho("🔐 Enabling passkey protection...", fg='cyan')
        self.passkey_manager.store_private_key(private_key)

        # Remove the plaintext private key file
        self.storage.remove_private_key_file()

        # Show success with appropriate message
        if isinstance(self.passkey_manager, MacPasskeyManager) if 'MacPasskeyManager' in globals() else False:
            click.secho("✅ Keychain passkey protection enabled!", fg='green')
            click.secho("   Private key moved to macOS Keychain.", fg='green')
            click.secho("   You'll be prompted for Touch ID/Face ID when accessing secrets.", fg='cyan')
        else:
            click.secho("✅ FIDO2 passkey protection enabled!", fg='green')
            click.secho("   Private key secured with your hardware key.", fg='green')
            click.secho("   You'll need your security key when accessing secrets.", fg='cyan')
    
    def rotate_keys(self):
        """Rotate encryption keys - generates new keys and re-encrypts all secrets."""
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Nothing to rotate.")

        # Load all secrets with current key
        click.secho("🔄 Starting key rotation...", fg='cyan')
        secrets = self.storage.load_secrets()
        if not secrets:
            raise VibeSafeError("No secrets to rotate. Key rotation aborted.")

        click.echo(f"Found {len(secrets)} secret(s) to re-encrypt.")

        # Load current private key (may trigger passkey auth)
        click.echo("🔓 Loading current private key...")
        old_private_key = self._load_private_key_with_auth()

        # Decrypt all secrets with old key
        click.echo("🔓 Decrypting secrets with current key...")
        decrypted_secrets = {}
        for name, encrypted_data in secrets.items():
            try:
                plaintext = self.encryption.decrypt_secret(encrypted_data, old_private_key)
                decrypted_secrets[name] = plaintext
            except Exception as e:
                raise VibeSafeError(f"Failed to decrypt secret '{name}' during rotation: {e}")

        # Generate new key pair
        click.echo("🔐 Generating new key pair...")
        new_private_key, new_public_key = self.encryption.generate_key_pair()

        # Re-encrypt all secrets with new key
        click.echo("🔒 Re-encrypting secrets with new key...")
        new_encrypted_secrets = {}
        for name, plaintext in decrypted_secrets.items():
            encrypted_data = self.encryption.encrypt_secret(plaintext, new_public_key)
            new_encrypted_secrets[name] = encrypted_data

        # Backup old keys (just in case)
        backup_dir = self.storage.base_dir / 'key_backup'
        backup_dir.mkdir(mode=0o700, exist_ok=True)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        if self.storage.private_key_file_exists():
            old_priv_backup = backup_dir / f'private_{timestamp}.pem'
            import shutil
            shutil.copy2(self.storage.priv_key_file, old_priv_backup)
            click.echo(f"💾 Backed up old private key to: {old_priv_backup}")

        old_pub_backup = backup_dir / f'public_{timestamp}.pem'
        import shutil
        shutil.copy2(self.storage.pub_key_file, old_pub_backup)
        click.echo(f"💾 Backed up old public key to: {old_pub_backup}")

        # Save new keys and re-encrypted secrets
        self.storage.save_keys(new_private_key, new_public_key)
        self.storage.save_secrets(new_encrypted_secrets)

        # If passkey was enabled, update it with new key
        if self.passkey_manager and self.passkey_manager.is_enabled():
            click.echo("🔐 Updating passkey protection with new key...")
            self.passkey_manager.store_private_key(new_private_key)
            self.storage.remove_private_key_file()

        click.secho("✅ Key rotation complete!", fg='green')
        click.secho(f"   • {len(new_encrypted_secrets)} secret(s) re-encrypted", fg='green')
        click.secho(f"   • Old keys backed up to: {backup_dir}", fg='cyan')
        click.secho("   • New keys are now active", fg='green')

    def export_backup(self, output_file: str = None, include_private_key: bool = False):
        """Export encrypted secrets and optionally keys for backup.

        Args:
            output_file: Path to output file (defaults to vibesafe_backup_<timestamp>.tar)
            include_private_key: Whether to include private key (security risk!)
        """
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Nothing to export.")

        # Generate default filename if not provided
        if output_file is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"vibesafe_backup_{timestamp}.tar"

        output_path = Path(output_file)

        # Create temporary directory for export files
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy secrets file
            if self.storage.secrets_file.exists():
                import shutil
                shutil.copy2(self.storage.secrets_file, temp_path / 'secrets.json')

            # Copy public key
            if self.storage.pub_key_file.exists():
                import shutil
                shutil.copy2(self.storage.pub_key_file, temp_path / 'public.pem')

            # Copy config
            if self.storage.config_file.exists():
                import shutil
                shutil.copy2(self.storage.config_file, temp_path / 'config.json')

            # Optionally include private key (with strong warning)
            if include_private_key:
                if self.storage.private_key_file_exists():
                    click.secho("⚠️  WARNING: Including private key in backup!", fg='red', err=True)
                    click.secho("   This backup contains sensitive key material.", fg='yellow', err=True)
                    click.secho("   Store it securely and never share it!", fg='yellow', err=True)
                    import shutil
                    shutil.copy2(self.storage.priv_key_file, temp_path / 'private.pem')
                else:
                    click.secho("⚠️  Private key is in secure storage (passkey), not included", fg='yellow')

            # Create tar archive
            with tarfile.open(output_path, 'w') as tar:
                for file in temp_path.iterdir():
                    tar.add(file, arcname=file.name)

        # Set restrictive permissions on backup file
        os.chmod(output_path, 0o600)

        secrets = self.storage.load_secrets()
        click.secho(f"✅ Backup exported to: {output_path}", fg='green')
        click.secho(f"   • {len(secrets)} secret(s) backed up", fg='cyan')
        click.secho(f"   • Public key included", fg='cyan')
        if include_private_key and self.storage.private_key_file_exists():
            click.secho(f"   • Private key included (⚠️ SENSITIVE)", fg='yellow')

    def import_backup(self, backup_file: str, force: bool = False):
        """Import secrets and keys from a backup file.

        Args:
            backup_file: Path to backup tar file
            force: Whether to overwrite existing data
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise VibeSafeError(f"Backup file not found: {backup_file}")

        # Check if data already exists
        if self.storage.key_exists() and not force:
            raise VibeSafeError("Keys already exist. Use --force to overwrite.")

        if self.storage.secrets_file.exists() and not force:
            existing_secrets = self.storage.load_secrets()
            if existing_secrets:
                raise VibeSafeError(f"{len(existing_secrets)} secret(s) already exist. Use --force to overwrite.")

        # Extract backup to temporary directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract tar archive
            try:
                with tarfile.open(backup_path, 'r') as tar:
                    # Validate tar members for security
                    for member in tar.getmembers():
                        # Ensure no path traversal
                        if member.name.startswith('..') or '/' in member.name:
                            raise VibeSafeError(f"Invalid tar member: {member.name}")
                    tar.extractall(temp_path)
            except tarfile.TarError as e:
                raise VibeSafeError(f"Failed to extract backup: {e}")

            # Import files
            imported = []

            # Import public key
            pub_key_backup = temp_path / 'public.pem'
            if pub_key_backup.exists():
                import shutil
                self.storage.base_dir.mkdir(mode=0o700, exist_ok=True)
                shutil.copy2(pub_key_backup, self.storage.pub_key_file)
                os.chmod(self.storage.pub_key_file, 0o644)
                imported.append('public key')

            # Import private key if present
            priv_key_backup = temp_path / 'private.pem'
            if priv_key_backup.exists():
                import shutil
                shutil.copy2(priv_key_backup, self.storage.priv_key_file)
                os.chmod(self.storage.priv_key_file, 0o600)
                imported.append('private key')

            # Import secrets
            secrets_backup = temp_path / 'secrets.json'
            if secrets_backup.exists():
                import shutil
                shutil.copy2(secrets_backup, self.storage.secrets_file)
                os.chmod(self.storage.secrets_file, 0o600)
                secrets = self.storage.load_secrets()
                imported.append(f'{len(secrets)} secret(s)')

            # Import config
            config_backup = temp_path / 'config.json'
            if config_backup.exists():
                import shutil
                shutil.copy2(config_backup, self.storage.config_file)
                os.chmod(self.storage.config_file, 0o600)
                imported.append('configuration')

        if not imported:
            raise VibeSafeError("No valid data found in backup file")

        click.secho(f"✅ Backup imported successfully!", fg='green')
        for item in imported:
            click.secho(f"   • Imported {item}", fg='cyan')

    def disable_passkey(self):
        """Disable passkey protection"""
        if not self.passkey_manager:
            raise VibeSafeError("Passkey support not available on this platform.")
        
        if not self.passkey_manager.is_enabled():
            raise VibeSafeError("Passkey protection is not enabled.")
        
        click.echo("Disabling passkey protection...")
        click.echo("You'll need to authenticate to export your private key...")
        
        # Retrieve private key from secure storage
        private_key = self.passkey_manager.retrieve_private_key()
        
        # Save back to file
        self.storage.save_private_key(private_key)
        
        # Remove from secure storage
        self.passkey_manager.remove_private_key()
        
        click.echo("✓ Passkey protection disabled. Private key exported to file.")
    
    # ======== Programmatic API Methods ========
    # These methods are designed for external tool integration
    # They return values directly instead of printing to stdout

    def fetch_secret(self, name: str) -> str:
        """Programmatic API to retrieve a secret value.

        This method returns the plaintext secret directly for use in scripts/tools.
        It should NEVER be used in contexts where the value might be logged or displayed.

        Note: For best performance with passkey authentication, consider creating
        a VibeSafe instance with interactive=False for API usage.

        Args:
            name: The name of the secret to retrieve

        Returns:
            The plaintext secret value

        Raises:
            VibeSafeError: If key pair not found or secret doesn't exist
        """
        # Temporarily suppress interactive mode for API calls if needed
        was_interactive = self.interactive
        if was_interactive:
            self.interactive = False
        try:
            return self.get_secret(name, return_value=True)
        finally:
            self.interactive = was_interactive

    def store_secret(self, name: str, value: str, overwrite: bool = False) -> None:
        """Programmatic API to store a secret.

        Args:
            name: The name of the secret
            value: The plaintext secret value
            overwrite: Whether to overwrite if secret exists

        Raises:
            VibeSafeError: If key pair not found or secret exists (without overwrite)
        """
        # Temporarily suppress interactive mode for API calls
        was_interactive = self.interactive
        if was_interactive:
            self.interactive = False
        try:
            # Use the existing add_secret method but with value provided
            self.add_secret(name, value, overwrite)
        finally:
            self.interactive = was_interactive

    def list_secret_names(self) -> list:
        """Programmatic API to get list of secret names.

        Returns:
            List of secret names (strings)
        """
        secrets = self.storage.load_secrets()
        return sorted(list(secrets.keys()))

    def secret_exists(self, name: str) -> bool:
        """Check if a secret exists.

        Args:
            name: The name of the secret

        Returns:
            True if secret exists, False otherwise
        """
        secrets = self.storage.load_secrets()
        return name in secrets

    def remove_secret(self, name: str) -> None:
        """Programmatic API to delete a secret.

        Args:
            name: The name of the secret to delete

        Raises:
            VibeSafeError: If secret doesn't exist
        """
        secrets = self.storage.load_secrets()
        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")
        del secrets[name]
        self.storage.save_secrets(secrets)

    def get_status_info(self) -> dict:
        """Get system status information as a dict.

        Returns:
            Dictionary with status information
        """
        status = {
            'initialized': self.storage.key_exists(),
            'passkey_enabled': False,
            'passkey_type': None,
            'secret_count': 0,
            'private_key_location': 'file' if self.storage.private_key_file_exists() else 'secure_storage'
        }

        if self.passkey_manager and self.passkey_manager.is_enabled():
            status['passkey_enabled'] = True
            if IS_MACOS:
                status['passkey_type'] = 'keychain'
            else:
                status['passkey_type'] = 'fido2'

        secrets = self.storage.load_secrets()
        status['secret_count'] = len(secrets)

        return status

    # ======== CLI Methods ========
    # These methods are designed for CLI use and print to stdout

    def show_status(self):
        """Show system status"""
        click.echo("VibeSafe Status")
        click.echo("=" * 40)

        # Key status
        if self.storage.key_exists():
            click.echo(f"✓ Key pair initialized")
            click.echo(f"  Public key:  {self.storage.pub_key_file}")
            if self.storage.private_key_file_exists():
                click.echo(f"  Private key: {self.storage.priv_key_file}")
            else:
                click.echo(f"  Private key: In secure storage")
        else:
            click.echo("✗ No key pair found")

        # Passkey status
        if self.passkey_manager and self.passkey_manager.is_enabled():
            click.echo(f"\n✓ Passkey protection: ENABLED")
            if IS_MACOS:
                click.echo("  Type: macOS Keychain (Touch ID/Face ID)")
            else:
                click.echo("  Type: FIDO2/WebAuthn")
        else:
            click.echo(f"\n✗ Passkey protection: DISABLED")

        # Claude integration status
        claude_file = Path.cwd() / "CLAUDE.md"
        config = self.storage.load_config()
        claude_configured = config.get('claude_configured', False) or claude_file.exists()

        if claude_configured:
            click.echo(f"\n✓ Claude Code integration: CONFIGURED")
            if claude_file.exists():
                click.echo(f"  Config file: {claude_file}")
        else:
            click.echo(f"\n✗ Claude Code integration: NOT CONFIGURED")
            click.echo("  Run 'vibesafe claude setup' in your project directory")

        # Check file permissions
        self._check_file_permissions()

        # Secrets count
        secrets = self.storage.load_secrets()
        click.echo(f"\nSecrets stored: {len(secrets)}")
    
    def _load_private_key_with_auth(self, silent=False, passphrase=None):
        """Load private key, handling passkey authentication if enabled

        Args:
            silent: If True, suppress authentication prompts (for API usage)
            passphrase: Optional passphrase for encrypted keys
        """
        if self.passkey_manager and self.passkey_manager.is_enabled():
            # This will trigger biometric/passkey authentication
            try:
                # Only show prompts if interactive and not silent
                if self.interactive and not silent:
                    click.echo("🔐 Touch ID/Face ID required to access secrets", err=True)
                    click.echo("👆 Please authenticate when prompted", err=True)

                return self.passkey_manager.retrieve_private_key()
            except PasskeyError as e:
                error_msg = str(e).lower()
                if "cancelled" in error_msg:
                    if self.interactive:
                        raise VibeSafeError("❌ Authentication cancelled. Please try again.")
                    else:
                        raise VibeSafeError("Authentication cancelled")
                elif "timeout" in error_msg:
                    if self.interactive:
                        raise VibeSafeError("⏰ Authentication timed out. Please try again.")
                    else:
                        raise VibeSafeError("Authentication timeout")
                elif "failed" in error_msg:
                    if self.interactive:
                        raise VibeSafeError("❌ Authentication failed. Please check your Touch ID/Face ID settings.")
                    else:
                        raise VibeSafeError("Authentication failed")
                raise VibeSafeError(f"Authentication error: {str(e)}")
        else:
            # Load from file (potentially with passphrase)
            return self.storage.load_private_key(passphrase)

    def _check_file_permissions(self):
        """Check and warn about insecure file permissions"""
        warnings = []

        # Check directory permissions
        if self.storage.base_dir.exists():
            dir_stat = os.stat(self.storage.base_dir)
            if dir_stat.st_mode & 0o077:  # Group/other have permissions
                perms = stat.filemode(dir_stat.st_mode)
                warnings.append(f"Directory {self.storage.base_dir}: {perms} (should be 700)")

        # Check private key if it exists as file
        if self.storage.private_key_file_exists():
            key_stat = os.stat(self.storage.priv_key_file)
            if key_stat.st_mode & 0o077:
                perms = stat.filemode(key_stat.st_mode)
                warnings.append(f"Private key: {perms} (should be 600)")

        # Check secrets file
        if self.storage.secrets_file.exists():
            secrets_stat = os.stat(self.storage.secrets_file)
            if secrets_stat.st_mode & 0o077:
                perms = stat.filemode(secrets_stat.st_mode)
                warnings.append(f"Secrets file: {perms} (should be 600)")

        if warnings:
            click.echo("\n⚠️  Security Warnings:")
            for warning in warnings:
                click.secho(f"  {warning}", fg='yellow')
            click.echo("  Fix with: chmod 700 ~/.vibesafe && chmod 600 ~/.vibesafe/*")

    def _validate_secret_name(self, name: str) -> bool:
        """Validate secret name for safety"""
        # Only allow alphanumeric, underscore, hyphen
        # Max length 100 chars
        if not name or len(name) > 100:
            return False
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))

    def _prompt_for_passphrase(self) -> str:
        """Prompt for passphrase to decrypt private key"""
        config = self.storage.load_config()
        if not config.get('key_encrypted', False):
            return None

        try:
            passphrase = getpass("Enter passphrase for private key: ")
            return passphrase
        except KeyboardInterrupt:
            raise VibeSafeError("\nPassphrase entry cancelled")


@click.group()
@click.version_option(version='1.0.0')
@click.pass_context
def cli(ctx):
    """VibeSafe - Secure Secrets Manager with Passkey Protection"""
    # Show welcome message for first-time users
    if ctx.invoked_subcommand is None:
        _show_welcome_message()


def _show_welcome_message():
    """Show welcome message and basic help"""
    storage = StorageManager()
    
    if not storage.key_exists():
        click.echo("🔐 Welcome to VibeSafe!")
        click.echo("=" * 40)
        click.echo("Secure secrets manager with passkey protection\n")
        click.echo("🚀 Quick start:")
        click.echo("   vibesafe setup     # Run interactive setup wizard")
        click.echo("   vibesafe init      # Initialize encryption keys")
        click.echo("   vibesafe --help    # Show all commands")
        click.echo("\n💡 For the best experience, run: vibesafe setup")
    else:
        click.echo("🔐 VibeSafe - Secure Secrets Manager")
        click.echo("Type 'vibesafe --help' for available commands")


@cli.command()
def init():
    """Initialize a new RSA key pair"""
    vibesafe = VibeSafe()
    try:
        vibesafe.init_keys()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def setup():
    """Run the interactive setup wizard"""
    from .setup_wizard import run_setup_wizard
    try:
        success = run_setup_wizard()
        if not success:
            click.echo("Setup was not completed successfully.")
            sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during setup: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.argument('value', required=False)
@click.option('--overwrite', '-o', is_flag=True, help='Overwrite if secret already exists')
def add(name, value, overwrite):
    """Add a new secret"""
    vibesafe = VibeSafe()
    try:
        vibesafe.add_secret(name, value, overwrite)
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
def get(name):
    """Retrieve a secret value"""
    vibesafe = VibeSafe()
    try:
        vibesafe.get_secret(name)
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def list():
    """List all stored secret names"""
    vibesafe = VibeSafe()
    try:
        vibesafe.list_secrets()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
def delete(name, yes):
    """Delete a stored secret"""
    vibesafe = VibeSafe()
    try:
        vibesafe.delete_secret(name, yes)
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show system status"""
    vibesafe = VibeSafe()
    try:
        vibesafe.show_status()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def passkey():
    """Manage passkey protection"""
    pass


@passkey.command('enable')
def passkey_enable():
    """Enable passkey protection (Touch ID/Face ID on macOS)"""
    vibesafe = VibeSafe()
    try:
        vibesafe.enable_passkey()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@passkey.command('disable')
def passkey_disable():
    """Disable passkey protection"""
    vibesafe = VibeSafe()
    try:
        vibesafe.disable_passkey()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
def rotate(yes):
    """Rotate encryption keys and re-encrypt all secrets"""
    vibesafe = VibeSafe()
    try:
        if not yes:
            click.secho("⚠️  Key rotation will:", fg='yellow')
            click.echo("   • Generate new encryption keys")
            click.echo("   • Re-encrypt all stored secrets")
            click.echo("   • Backup old keys (just in case)")
            click.echo("")
            if not click.confirm("Continue with key rotation?"):
                click.echo("Key rotation cancelled.")
                return
        vibesafe.rotate_keys()
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('export')
@click.option('--output', '-o', help='Output file path (default: vibesafe_backup_<timestamp>.tar)')
@click.option('--include-private-key', is_flag=True, help='Include private key (SENSITIVE!)')
def export_backup(output, include_private_key):
    """Export secrets and keys for backup"""
    vibesafe = VibeSafe()
    try:
        if include_private_key:
            click.secho("⚠️  WARNING: You are about to export your private key!", fg='red')
            click.secho("   This backup will contain highly sensitive data.", fg='yellow')
            if not click.confirm("Are you sure you want to include the private key?"):
                click.echo("Export cancelled.")
                return
        vibesafe.export_backup(output, include_private_key)
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('import')
@click.argument('backup_file')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing data')
def import_backup(backup_file, force):
    """Import secrets and keys from backup file"""
    vibesafe = VibeSafe()
    try:
        if force:
            click.secho("⚠️  WARNING: This will overwrite existing data!", fg='yellow')
            if not click.confirm("Continue with import?"):
                click.echo("Import cancelled.")
                return
        vibesafe.import_backup(backup_file, force)
    except VibeSafeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Removed unused passkey command implementations


@cli.group()
def claude():
    """Claude Code integration commands"""
    pass


@claude.command('setup')
@click.option('--project-dir', help='Project directory (default: current directory)')
def claude_setup(project_dir):
    """Set up Claude Code integration"""
    from .claude_integration import setup_claude_integration
    try:
        claude_file = setup_claude_integration(project_dir)
        click.echo(f"\n🎉 Claude Code integration is ready!")
        click.echo(f"📝 Configuration saved to: {claude_file}")
    except Exception as e:
        click.echo(f"Error setting up Claude integration: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()