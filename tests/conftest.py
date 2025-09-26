"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from pathlib import Path
from click.testing import CliRunner

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def cleanup_env(monkeypatch):
    """Clean up environment for each test"""
    # Ensure tests don't affect real home directory
    monkeypatch.setenv('VIBESAFE_TEST', '1')
    
    # Mock platform for consistent testing
    if os.getenv('TEST_PLATFORM'):
        import platform
        monkeypatch.setattr(platform, 'system', lambda: os.getenv('TEST_PLATFORM'))


@pytest.fixture
def mock_macos(monkeypatch):
    """Mock macOS environment"""
    import platform
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    

@pytest.fixture
def mock_linux(monkeypatch):
    """Mock Linux environment"""
    import platform
    monkeypatch.setattr(platform, 'system', lambda: 'Linux')


@pytest.fixture
def mock_windows(monkeypatch):
    """Mock Windows environment"""
    import platform
    monkeypatch.setattr(platform, 'system', lambda: 'Windows')


@pytest.fixture
def temp_dir(tmp_path, monkeypatch):
    """Create temporary directory for testing"""
    # Set up isolated environment
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    return str(tmp_path)


@pytest.fixture
def runner(temp_dir):
    """Create a CLI runner with isolated environment"""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=temp_dir):
        yield runner