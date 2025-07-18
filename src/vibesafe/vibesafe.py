#!/usr/bin/env python3
"""
VibeSafe - Secure Secrets Manager CLI with Passkey Protection
"""
import os
import sys
import json
import base64
import platform
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
    def __init__(self):
        self.storage = StorageManager()
        self.encryption = EncryptionManager()
        
        # Initialize passkey manager if available
        self.passkey_manager = None
        if IS_MACOS and PASSKEY_AVAILABLE:
            self.passkey_manager = MacPasskeyManager()
            self.passkey_manager.storage = self.storage
        elif FIDO2_AVAILABLE:
            self.passkey_manager = Fido2PasskeyManager()
    
    def init_keys(self):
        """Initialize a new RSA key pair"""
        if self.storage.key_exists():
            raise VibeSafeError("Key pair already exists. Use --force to regenerate.")
        
        click.echo("Generating new RSA key pair...")
        private_key, public_key = self.encryption.generate_key_pair()
        
        self.storage.save_keys(private_key, public_key)
        click.echo(f"✓ Public key saved to:  {self.storage.pub_key_file}")
        click.echo(f"✓ Private key saved to: {self.storage.priv_key_file}")
        click.echo("\n⚠️  Keep your private key safe! If lost, you cannot decrypt existing secrets.")
    
    def add_secret(self, name, value=None, overwrite=False):
        """Add a new secret"""
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")
        
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
        
        click.echo(f"✓ Secret '{name}' has been added and encrypted.")
    
    def get_secret(self, name):
        """Retrieve and decrypt a secret"""
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")
        
        secrets = self.storage.load_secrets()
        if name not in secrets:
            raise VibeSafeError(f"Secret '{name}' not found.")
        
        # Load private key (may trigger passkey authentication)
        private_key = self._load_private_key_with_auth()
        
        # Decrypt secret
        encrypted_data = secrets[name]
        try:
            plaintext = self.encryption.decrypt_secret(encrypted_data, private_key)
            # Write directly to stdout buffer to avoid encoding issues
            # This ensures the secret goes directly to the destination without being visible
            sys.stdout.buffer.write(plaintext.encode('utf-8'))
        except Exception as e:
            # Don't include decryption details in error message for security
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
    
    def enable_passkey(self):
        """Enable passkey protection"""
        if not self.passkey_manager:
            raise VibeSafeError("Passkey support not available on this platform.")
        
        if not self.storage.key_exists():
            raise VibeSafeError("No key pair found. Run 'vibesafe init' first.")
        
        # Load existing private key
        private_key = self.storage.load_private_key()
        
        # Store in secure storage (Keychain on macOS, encrypted with FIDO2 elsewhere)
        click.echo("Enabling passkey protection...")
        self.passkey_manager.store_private_key(private_key)
        
        # Remove the plaintext private key file
        self.storage.remove_private_key_file()
        
        click.echo("✓ Passkey protection enabled. Private key moved to secure storage.")
        click.echo("  You'll be prompted for biometric authentication when accessing secrets.")
    
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
        
        # Secrets count
        secrets = self.storage.load_secrets()
        click.echo(f"\nSecrets stored: {len(secrets)}")
    
    def _load_private_key_with_auth(self):
        """Load private key, handling passkey authentication if enabled"""
        if self.passkey_manager and self.passkey_manager.is_enabled():
            # This will trigger biometric/passkey authentication
            try:
                # Inform user about authentication requirement
                click.echo("🔐 Touch ID/Face ID required to access secrets", err=True)
                click.echo("👆 Please authenticate when prompted", err=True)
                
                return self.passkey_manager.retrieve_private_key()
            except PasskeyError as e:
                if "cancelled" in str(e).lower():
                    raise VibeSafeError("❌ Authentication cancelled. Please try again.")
                elif "timeout" in str(e).lower():
                    raise VibeSafeError("⏰ Authentication timed out. Please try again.")
                elif "failed" in str(e).lower():
                    raise VibeSafeError("❌ Authentication failed. Please check your Touch ID/Face ID settings.")
                raise VibeSafeError(f"Authentication error: {str(e)}")
        else:
            # Load from file
            return self.storage.load_private_key()


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