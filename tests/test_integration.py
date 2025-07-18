"""
Integration tests for VibeSafe
"""
import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from vibesafe.vibesafe import cli


class TestIntegration:
    @pytest.mark.integration
    def test_full_workflow(self, runner):
        """Test complete workflow from init to delete"""
        # Initialize
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0
        
        # Add multiple secrets
        secrets = {
            'API_KEY': 'sk-1234567890',
            'DB_PASSWORD': 'super_secret_password',
            'JWT_SECRET': 'jwt_secret_key_123',
            'OAUTH_TOKEN': 'oauth_token_xyz'
        }
        
        for name, value in secrets.items():
            result = runner.invoke(cli, ['add', name, value])
            assert result.exit_code == 0
        
        # List secrets
        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        for name in secrets:
            assert name in result.output
        
        # Retrieve each secret
        for name, expected_value in secrets.items():
            result = runner.invoke(cli, ['get', name])
            assert result.exit_code == 0
            assert result.output == expected_value
        
        # Update a secret
        result = runner.invoke(cli, ['add', '--overwrite', 'API_KEY', 'new_key_value'])
        assert result.exit_code == 0
        
        # Verify update
        result = runner.invoke(cli, ['get', 'API_KEY'])
        assert result.exit_code == 0
        assert result.output == 'new_key_value'
        
        # Delete a secret
        result = runner.invoke(cli, ['delete', '--yes', 'JWT_SECRET'])
        assert result.exit_code == 0
        
        # Verify deletion
        result = runner.invoke(cli, ['list'])
        assert 'JWT_SECRET' not in result.output
        
        # Check status
        result = runner.invoke(cli, ['status'])
        assert result.exit_code == 0
        assert 'Secrets stored: 3' in result.output
    
    @pytest.mark.integration
    def test_cli_subprocess(self, temp_dir):
        """Test CLI through subprocess (more realistic)"""
        # Set HOME to temp directory
        env = os.environ.copy()
        env['HOME'] = temp_dir
        env['USERPROFILE'] = temp_dir  # Windows
        
        # Helper function to run vibesafe
        def run_vibesafe(args):
            cmd = [sys.executable, '-m', 'vibesafe'] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd=Path(__file__).parent.parent
            )
            return result
        
        # Test workflow
        result = run_vibesafe(['init'])
        assert result.returncode == 0
        assert 'Generated a new RSA key pair' in result.stdout
        
        # Add and get secret
        result = run_vibesafe(['add', 'TEST_KEY', 'test_value'])
        assert result.returncode == 0
        
        result = run_vibesafe(['get', 'TEST_KEY'])
        assert result.returncode == 0
        assert result.stdout.strip() == 'test_value'
    
    @pytest.mark.integration
    def test_error_recovery(self, runner):
        """Test error handling and recovery"""
        # Try operations without init
        result = runner.invoke(cli, ['add', 'KEY', 'value'])
        assert result.exit_code == 1
        assert 'No key pair found' in result.output
        
        # Initialize
        runner.invoke(cli, ['init'])
        
        # Try to get non-existent secret
        result = runner.invoke(cli, ['get', 'NONEXISTENT'])
        assert result.exit_code == 1
        
        # Add secret and verify we can still continue
        result = runner.invoke(cli, ['add', 'REAL_KEY', 'real_value'])
        assert result.exit_code == 0
        
        result = runner.invoke(cli, ['get', 'REAL_KEY'])
        assert result.exit_code == 0
        assert result.output == 'real_value'
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_secret_handling(self, runner):
        """Test handling of large secrets"""
        # Initialize
        runner.invoke(cli, ['init'])
        
        # Create large secret (1MB)
        large_secret = 'A' * (1024 * 1024)
        
        # Add large secret
        result = runner.invoke(cli, ['add', 'LARGE_SECRET', large_secret])
        assert result.exit_code == 0
        
        # Retrieve it
        result = runner.invoke(cli, ['get', 'LARGE_SECRET'])
        assert result.exit_code == 0
        assert result.output == large_secret
        
        # List should still work
        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0
        assert 'LARGE_SECRET' in result.output
    
    @pytest.mark.integration
    def test_special_characters(self, runner):
        """Test handling of special characters in secrets"""
        # Initialize
        runner.invoke(cli, ['init'])
        
        # Test various special characters
        special_secrets = {
            'SPECIAL1': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            'SPECIAL2': "Single'Quote\"Double",
            'SPECIAL3': 'New\nLine\tTab',
            'SPECIAL4': '\\Backslash/Forward',
            'SPECIAL5': '`Backtick~Tilde'
        }
        
        for name, value in special_secrets.items():
            # Add via input to avoid shell escaping issues
            result = runner.invoke(cli, ['add', name], input=value)
            assert result.exit_code == 0
            
            # Retrieve and verify
            result = runner.invoke(cli, ['get', name])
            assert result.exit_code == 0
            assert result.output == value


import sys  # Add this import for subprocess test