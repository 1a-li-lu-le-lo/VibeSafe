"""
Test suite for CLI functionality
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from vibesafe.vibesafe import cli
from vibesafe.storage import StorageManager
from vibesafe.encryption import EncryptionManager


class TestCLI:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def runner(self, temp_dir, monkeypatch):
        """Create CLI runner with isolated environment"""
        runner = CliRunner()
        # Override home directory for testing
        monkeypatch.setenv('HOME', temp_dir)
        monkeypatch.setenv('USERPROFILE', temp_dir)  # Windows
        return runner
    
    @pytest.fixture
    def initialized_vibesafe(self, runner):
        """Initialize VibeSafe for testing"""
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0
        return runner
    
    def test_version(self, runner):
        """Test version command"""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output
    
    def test_init_command(self, runner):
        """Test initialization"""
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0
        assert 'Generating new RSA key pair' in result.output
        assert 'Public key saved to:' in result.output
        assert 'Private key saved to:' in result.output
    
    def test_init_already_exists(self, initialized_vibesafe):
        """Test initialization when keys already exist"""
        result = initialized_vibesafe.invoke(cli, ['init'])
        assert result.exit_code == 1
        assert 'Key pair already exists' in result.output
    
    def test_add_secret(self, initialized_vibesafe):
        """Test adding a secret"""
        result = initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'test_value'])
        assert result.exit_code == 0
        assert "Secret 'TEST_KEY' has been added and encrypted" in result.output
    
    def test_add_secret_with_prompt(self, initialized_vibesafe):
        """Test adding a secret with prompt"""
        result = initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY'], input='secret_value\n')
        assert result.exit_code == 0
        assert "Secret 'TEST_KEY' has been added and encrypted" in result.output
    
    def test_add_existing_secret(self, initialized_vibesafe):
        """Test adding existing secret without overwrite"""
        # Add initial secret
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value1'])
        
        # Try to add again
        result = initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value2'])
        assert result.exit_code == 1
        assert "already exists" in result.output
    
    def test_add_with_overwrite(self, initialized_vibesafe):
        """Test overwriting existing secret"""
        # Add initial secret
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value1'])
        
        # Overwrite
        result = initialized_vibesafe.invoke(cli, ['add', '--overwrite', 'TEST_KEY', 'value2'])
        assert result.exit_code == 0
        assert "Secret 'TEST_KEY' has been added and encrypted" in result.output
    
    def test_get_secret(self, initialized_vibesafe):
        """Test retrieving a secret"""
        # Add a secret
        test_value = 'test_secret_123'
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', test_value])
        
        # Get it back
        result = initialized_vibesafe.invoke(cli, ['get', 'TEST_KEY'])
        assert result.exit_code == 0
        assert result.output == test_value  # Should output only the value
    
    def test_get_nonexistent_secret(self, initialized_vibesafe):
        """Test getting non-existent secret"""
        result = initialized_vibesafe.invoke(cli, ['get', 'NONEXISTENT'])
        assert result.exit_code == 1
        assert "not found" in result.output
    
    def test_list_secrets(self, initialized_vibesafe):
        """Test listing secrets"""
        # Add some secrets
        initialized_vibesafe.invoke(cli, ['add', 'KEY1', 'value1'])
        initialized_vibesafe.invoke(cli, ['add', 'KEY2', 'value2'])
        initialized_vibesafe.invoke(cli, ['add', 'KEY3', 'value3'])
        
        # List them
        result = initialized_vibesafe.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert 'KEY1' in result.output
        assert 'KEY2' in result.output
        assert 'KEY3' in result.output
    
    def test_list_empty(self, initialized_vibesafe):
        """Test listing when no secrets exist"""
        result = initialized_vibesafe.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert 'No secrets stored' in result.output
    
    def test_delete_secret(self, initialized_vibesafe):
        """Test deleting a secret with confirmation"""
        # Add a secret
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value'])
        
        # Delete with confirmation
        result = initialized_vibesafe.invoke(cli, ['delete', 'TEST_KEY'], input='y\n')
        assert result.exit_code == 0
        assert "Secret 'TEST_KEY' has been deleted" in result.output
        
        # Verify it's gone
        result = initialized_vibesafe.invoke(cli, ['get', 'TEST_KEY'])
        assert result.exit_code == 1
    
    def test_delete_with_yes_flag(self, initialized_vibesafe):
        """Test deleting with --yes flag"""
        # Add a secret
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value'])
        
        # Delete without confirmation
        result = initialized_vibesafe.invoke(cli, ['delete', '--yes', 'TEST_KEY'])
        assert result.exit_code == 0
        assert "Secret 'TEST_KEY' has been deleted" in result.output
    
    def test_delete_cancelled(self, initialized_vibesafe):
        """Test cancelling deletion"""
        # Add a secret
        initialized_vibesafe.invoke(cli, ['add', 'TEST_KEY', 'value'])
        
        # Cancel deletion
        result = initialized_vibesafe.invoke(cli, ['delete', 'TEST_KEY'], input='n\n')
        assert result.exit_code == 0
        assert 'Deletion cancelled' in result.output
        
        # Verify it still exists
        result = initialized_vibesafe.invoke(cli, ['get', 'TEST_KEY'])
        assert result.exit_code == 0
    
    def test_status_command(self, initialized_vibesafe):
        """Test status command"""
        # Add some secrets
        initialized_vibesafe.invoke(cli, ['add', 'KEY1', 'value1'])
        initialized_vibesafe.invoke(cli, ['add', 'KEY2', 'value2'])
        
        result = initialized_vibesafe.invoke(cli, ['status'])
        assert result.exit_code == 0
        assert 'VibeSafe Status' in result.output
        assert 'Key pair initialized' in result.output
        assert 'Secrets stored: 2' in result.output
        assert 'Passkey protection: DISABLED' in result.output
    
    def test_commands_without_init(self, runner):
        """Test commands fail properly without initialization"""
        # Test add
        result = runner.invoke(cli, ['add', 'KEY', 'value'])
        assert result.exit_code == 1
        assert 'No key pair found' in result.output
        
        # Test get
        result = runner.invoke(cli, ['get', 'KEY'])
        assert result.exit_code == 1
        assert 'No key pair found' in result.output
        
        # Test delete
        result = runner.invoke(cli, ['delete', 'KEY'])
        assert result.exit_code == 1
    
    def test_unicode_secrets(self, initialized_vibesafe):
        """Test handling Unicode in secrets"""
        unicode_value = 'Hello 世界 🔐'
        
        # Add Unicode secret
        result = initialized_vibesafe.invoke(cli, ['add', 'UNICODE_KEY', unicode_value])
        assert result.exit_code == 0
        
        # Get it back
        result = initialized_vibesafe.invoke(cli, ['get', 'UNICODE_KEY'])
        assert result.exit_code == 0
        assert result.output == unicode_value