"""
VibeSafe Setup Wizard
Interactive setup process for new users
"""
import os
import platform
import click
from pathlib import Path
from .claude_integration import setup_claude_integration
from .storage import StorageManager
from .exceptions import VibeSafeError


class SetupWizard:
    def __init__(self):
        self.storage = StorageManager()
        self.is_macos = platform.system() == 'Darwin'
        self.has_touch_id = False
        self.setup_complete = False
        
        # Check for Touch ID/Face ID availability
        if self.is_macos:
            self.has_touch_id = self._check_biometric_availability()
    
    def _check_biometric_availability(self):
        """Check if biometric authentication is available"""
        try:
            from .mac_passkey import MacPasskeyManager
            manager = MacPasskeyManager()
            return manager.test_authentication()
        except Exception:
            return False
    
    def run_setup(self):
        """Run the complete setup wizard"""
        click.echo("\n" + "="*60)
        click.echo("🔐 Welcome to VibeSafe Setup Wizard!")
        click.echo("="*60)
        click.echo("Let's get you set up with secure secret management.\n")
        
        # Step 1: Initialize VibeSafe
        if not self._step_initialize():
            return False
        
        # Step 2: Add first secret
        if not self._step_add_first_secret():
            return False
        
        # Step 3: Setup passkey protection (if available)
        if not self._step_setup_passkey():
            return False
        
        # Step 4: Claude Code integration
        if not self._step_claude_integration():
            return False
        
        # Step 5: Show completion summary
        self._step_completion_summary()
        
        self.setup_complete = True
        return True
    
    def _step_initialize(self):
        """Step 1: Initialize VibeSafe"""
        click.echo("📋 Step 1: Initialize VibeSafe")
        click.echo("-" * 30)
        
        if self.storage.key_exists():
            click.echo("✅ VibeSafe is already initialized!")
            return True
        
        click.echo("🔑 Generating your encryption keys...")
        
        try:
            from .vibesafe import VibeSafe
            vibesafe = VibeSafe()
            vibesafe.init_keys()
            click.secho("✅ Encryption keys generated successfully!", fg='green')
            return True
        except Exception as e:
            click.secho(f"❌ Failed to initialize VibeSafe: {e}", fg='red', err=True)
            return False
    
    def _step_add_first_secret(self):
        """Step 2: Add first secret"""
        click.echo("\n📋 Step 2: Add Your First Secret")
        click.echo("-" * 35)
        
        # Check if secrets already exist
        secrets = self.storage.load_secrets()
        if secrets:
            click.echo(f"✅ You already have {len(secrets)} secret(s) stored!")
            return True
        
        click.echo("Let's add a test secret to verify everything works.")
        click.echo("(You can delete this later with: vibesafe delete DEMO_KEY)")
        
        # Add demo secret
        demo_key = "DEMO_KEY"
        demo_value = "demo_value_123"
        
        try:
            from .vibesafe import VibeSafe
            vibesafe = VibeSafe()
            vibesafe.add_secret(demo_key, demo_value)
            click.secho(f"✅ Demo secret '{demo_key}' added successfully!", fg='green')
            
            # Test retrieval with return_value parameter
            retrieved = vibesafe.get_secret(demo_key, return_value=True)
            if retrieved == demo_value:
                click.secho("✅ Secret retrieval test passed!", fg='green')
                return True
            else:
                click.secho("❌ Secret retrieval test failed!", fg='red')
                return False
                
        except Exception as e:
            click.secho(f"❌ Failed to add demo secret: {e}", fg='red', err=True)
            return False
    
    def _step_setup_passkey(self):
        """Step 3: Setup passkey protection"""
        click.echo("\n📋 Step 3: Passkey Protection Setup")
        click.echo("-" * 37)
        
        if not self.is_macos:
            click.echo("ℹ️  Passkey protection is only available on macOS")
            click.echo("   Your secrets are still securely encrypted at rest.")
            return True
        
        if not self.has_touch_id:
            click.echo("ℹ️  Touch ID/Face ID not available on this Mac")
            click.echo("   Your secrets are still securely encrypted at rest.")
            return True
        
        click.secho("🎉 Touch ID/Face ID is available on your Mac!", fg='cyan')
        click.echo("\n💡 Choose your passkey protection method:")
        click.echo("   1. 🔐 VibeSafe Keychain (Touch ID/Face ID)")
        click.echo("      • Private key stored in macOS Keychain")
        click.echo("      • Requires Touch ID/Face ID to access secrets")
        click.echo("      • Device-specific protection")
        click.echo("   2. 🍎 Apple Passkey (FIDO2/WebAuthn)")
        click.echo("      • True Apple Passkey following FIDO2 standards")
        click.echo("      • Syncs across all Apple devices")
        click.echo("      • Industry-standard implementation")

        # Check if FIDO2 is available
        try:
            from .fido2_passkey import Fido2PasskeyManager
            has_fido2 = True
        except ImportError:
            has_fido2 = False

        # Ask user which method they prefer
        choice = click.prompt("\n🔒 Choose passkey method (1/2) or press Enter to skip", default='', type=str)

        if choice == '1':
            # Use Keychain (default macOS implementation)
            try:
                from .vibesafe import VibeSafe
                vibesafe = VibeSafe(passkey_type='keychain')
                vibesafe.enable_passkey(passkey_type='keychain')
                click.secho("✅ Keychain passkey protection enabled!", fg='green')
                click.secho("   You'll be prompted for Touch ID/Face ID when accessing secrets.", fg='cyan')
                return True
            except Exception as e:
                click.secho(f"⚠️  Failed to enable Keychain passkey: {e}", fg='yellow')
                click.echo("   Don't worry - your secrets are still securely encrypted.")
                return True
        elif choice == '2':
            if not has_fido2:
                click.secho("⚠️  FIDO2 support not installed.", fg='yellow')
                click.echo("   Install with: pip install 'vibesafe[fido2]'")
                return True
            try:
                from .vibesafe import VibeSafe
                vibesafe = VibeSafe(passkey_type='fido2')
                vibesafe.enable_passkey(passkey_type='fido2')
                click.secho("✅ FIDO2 passkey protection enabled!", fg='green')
                click.secho("   Your private key is now secured with Apple Passkey.", fg='cyan')
                return True
            except Exception as e:
                click.secho(f"⚠️  Failed to enable FIDO2 passkey: {e}", fg='yellow')
                click.echo("   Don't worry - your secrets are still securely encrypted.")
                return True
        else:
            click.echo("⏭️  Skipping passkey protection setup")
            click.echo("   You can enable it later with: vibesafe passkey enable")
            return True
    
    def _step_claude_integration(self):
        """Step 4: Claude Code integration"""
        click.echo("\n📋 Step 4: Claude Code Integration")
        click.echo("-" * 35)
        
        click.echo("🤖 VibeSafe can automatically configure Claude Code")
        click.echo("   to use secure secret management.")
        
        # Ask user if they want Claude integration
        if click.confirm("\n📝 Would you like to set up Claude Code integration?", default=True):
            try:
                claude_file = setup_claude_integration()
                click.echo("✅ Claude Code integration configured!")
                return True
            except Exception as e:
                click.echo(f"⚠️  Failed to setup Claude integration: {e}")
                click.echo("   You can set this up manually later.")
                return True
        else:
            click.echo("⏭️  Skipping Claude Code integration")
            click.echo("   You can set this up later with: vibesafe setup claude")
            return True
    
    def _step_completion_summary(self):
        """Step 5: Show completion summary"""
        click.echo("\n" + "="*60)
        click.echo("🎉 VibeSafe Setup Complete!")
        click.echo("="*60)
        
        # Show what was configured
        click.echo("\n✅ What's configured:")
        click.echo("   • Secure encryption keys generated")
        click.echo("   • Demo secret added for testing")
        
        # Check passkey status
        from .vibesafe import VibeSafe
        vibesafe = VibeSafe()
        if vibesafe.passkey_manager and vibesafe.passkey_manager.is_enabled():
            click.echo("   • Passkey protection enabled (Touch ID/Face ID)")
        else:
            click.echo("   • File-based encryption (secure at rest)")
        
        # Show CLAUDE.md status
        claude_file = Path.cwd() / "CLAUDE.md"
        if claude_file.exists():
            click.echo("   • Claude Code integration configured")
        
        click.echo("\n🚀 Next Steps:")
        click.echo("   1. Add your real secrets:")
        click.echo("      vibesafe add API_KEY")
        click.echo("      vibesafe add DATABASE_URL")
        click.echo("   2. List your secrets:")
        click.echo("      vibesafe list")
        click.echo("   3. Use in your projects:")
        click.echo("      export API_KEY=$(vibesafe get API_KEY)")
        click.echo("   4. Delete the demo secret:")
        click.echo("      vibesafe delete DEMO_KEY")
        
        if self.has_touch_id:
            click.echo("\n🔒 Security Tips:")
            click.echo("   • First secret access will prompt for Touch ID/Face ID")
            click.echo("   • Keychain access is cached for the session")
            click.echo("   • Private key never leaves secure hardware")
        
        click.echo("\n📖 For help:")
        click.echo("   vibesafe --help")
        click.echo("   vibesafe status")
        
        click.echo("\n🔐 Your secrets are now secure with VibeSafe!")


def run_setup_wizard():
    """Run the setup wizard"""
    wizard = SetupWizard()
    return wizard.run_setup()


def run_quick_setup():
    """Run a quick setup without interactive prompts"""
    click.echo("🔧 Running VibeSafe quick setup...")
    
    try:
        from .vibesafe import VibeSafe
        vibesafe = VibeSafe()
        
        # Initialize if needed
        if not vibesafe.storage.key_exists():
            vibesafe.init_keys()
            click.echo("✅ VibeSafe initialized")
        
        # Setup Claude integration
        setup_claude_integration()
        click.echo("✅ Claude Code integration configured")
        
        click.echo("\n🎉 Quick setup complete!")
        click.echo("💡 Run 'vibesafe setup' for full interactive setup")
        
        return True
    except Exception as e:
        click.echo(f"❌ Quick setup failed: {e}")
        return False