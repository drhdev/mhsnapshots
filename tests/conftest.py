import os
import pytest
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Set up test environment variables and directories, and patch os.getcwd."""
    # Create necessary directories
    configs_dir = tmp_path / "configs"
    logs_dir = tmp_path / "logs"
    configs_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Set environment variables
    os.environ['PROJECT_ROOT'] = str(tmp_path)
    os.environ['CONFIGS_DIR'] = str(configs_dir)
    os.environ['LOGS_DIR'] = str(logs_dir)

    # Patch os.getcwd globally for all tests
    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    yield

    # Cleanup
    for env_var in ['PROJECT_ROOT', 'CONFIGS_DIR', 'LOGS_DIR']:
        if env_var in os.environ:
            del os.environ[env_var] 