"""
Test suite for passkey functionality
Note: These are unit tests that mock the actual biometric/FIDO2 interactions
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import platform


class TestPasskeyIntegration:
    @pytest.mark.skipif(platform.system() != 'Darwin', reason="macOS only test")
    def test_mac_passkey_available(self):
        """Test that macOS passkey is available on Darwin"""
        from vibesafe.vibesafe import IS_MACOS, PASSKEY_AVAILABLE
        assert IS_MACOS is True
        # PASSKEY_AVAILABLE depends on pyobjc installation
    
    def test_passkey_enable_without_init(self, runner):
        """Test enabling passkey without initialization"""
        from vibesafe.vibesafe import cli
        result = runner.invoke(cli, ['passkey', 'enable'])
        assert result.exit_code == 1
        assert 'No key pair found' in result.output
    
    @patch('vibesafe.mac_passkey.Security')
    @patch('vibesafe.mac_passkey.LocalAuthentication')
    def test_mac_passkey_store_retrieve(self, mock_la, mock_security, mock_macos):
        """Test macOS Keychain storage and retrieval"""
        from vibesafe.mac_passkey import MacPasskeyManager
        from vibesafe.encryption import EncryptionManager
        
        # Mock Security framework responses
        mock_security.SecItemAdd.return_value = 0  # Success
        mock_security.SecItemCopyMatching.return_value = (b'test_key_data', None)
        mock_security.kSecAccessControlUserPresence = 1
        
        manager = MacPasskeyManager()
        em = EncryptionManager()
        private_key, _ = em.generate_key_pair()
        
        # Test store
        manager.store_private_key(private_key)
        assert mock_security.SecItemAdd.called
        
        # Test retrieve
        with patch.object(em, 'deserialize_private_key', return_value=private_key):
            retrieved = manager.retrieve_private_key()
            assert mock_security.SecItemCopyMatching.called
    
    @patch('vibesafe.mac_passkey.Security')
    def test_mac_passkey_auth_cancelled(self, mock_security, mock_macos):
        """Test handling of cancelled authentication"""
        from vibesafe.mac_passkey import MacPasskeyManager
        from vibesafe.exceptions import AuthenticationError
        
        # Mock authentication cancelled
        mock_security.SecItemCopyMatching.return_value = (None, -128)
        
        manager = MacPasskeyManager()
        
        with pytest.raises(AuthenticationError) as exc_info:
            manager.retrieve_private_key()
        assert "cancelled" in str(exc_info.value).lower()
    
    def test_fido2_passkey_registration(self):
        """Test FIDO2 passkey registration flow"""
        from vibesafe.fido2_passkey import Fido2PasskeyManager
        
        with patch('vibesafe.fido2_passkey.Fido2Client') as mock_client:
            with patch('vibesafe.fido2_passkey.CtapHidDevice') as mock_device:
                # Mock device discovery
                mock_device.list_devices.return_value = [Mock()]
                
                # Mock registration response
                mock_result = Mock()
                mock_result.client_data = b'client_data'
                mock_result.attestation_object = b'attestation_object'
                mock_client.return_value.make_credential.return_value = mock_result
                
                # Mock server response
                mock_auth_data = Mock()
                mock_auth_data.credential_data.credential_id = b'cred_id'
                mock_auth_data.credential_data.public_key = b'pub_key'
                mock_auth_data.credential_data.aaguid = b'aaguid'
                
                manager = Fido2PasskeyManager()
                with patch.object(manager.server, 'register_complete', return_value=mock_auth_data):
                    result = manager.register_passkey()
                    
                    assert 'credential_id' in result
                    assert 'public_key' in result
    
    def test_passkey_status_display(self, initialized_vibesafe):
        """Test passkey status in status command"""
        result = initialized_vibesafe.invoke(['status'])
        assert result.exit_code == 0
        assert 'Passkey protection: DISABLED' in result.output