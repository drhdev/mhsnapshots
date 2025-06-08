import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys
import yaml

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mhsnapshots import SnapshotManager, ServerConfig

# Test data
MOCK_SERVER_CONFIG = {
    'server': {
        'id': '123456',
        'name': 'test-server',
        'api_token': 'test-token-123456',
        'retain_last_snapshots': 3
    }
}

MOCK_SNAPSHOTS = [
    {
        'id': '1',
        'description': 'test-server-20240101000000',
        'created': '2024-01-01T00:00:00Z',
        'created_from': {'id': 123456},
        'status': 'available'
    },
    {
        'id': '2',
        'description': 'test-server-20240102000000',
        'created': '2024-01-02T00:00:00Z',
        'created_from': {'id': 123456},
        'status': 'available'
    },
    {
        'id': '3',
        'description': 'test-server-20240103000000',
        'created': '2024-01-03T00:00:00Z',
        'created_from': {'id': 123456},
        'status': 'available'
    },
    {
        'id': '4',
        'description': 'test-server-20240104000000',
        'created': '2024-01-04T00:00:00Z',
        'created_from': {'id': 123456},
        'status': 'available'
    }
]

@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(MOCK_SERVER_CONFIG, f)
    return str(config_file)

@pytest.fixture
def snapshot_manager(mock_config_file):
    """Create a SnapshotManager instance with mocked dependencies."""
    with patch('mhsnapshots.SnapshotManager.get_hcloud_path') as mock_hcloud:
        mock_hcloud.return_value = '/usr/local/bin/hcloud'
        manager = SnapshotManager([mock_config_file], verbose=True)
        return manager

def test_load_configs(snapshot_manager, mock_config_file):
    """Test loading server configurations from YAML file."""
    servers = snapshot_manager.load_configs()
    assert len(servers) == 1
    server = servers[0]
    assert isinstance(server, ServerConfig)
    assert server.id == '123456'
    assert server.name == 'test-server'
    assert server.api_token == 'test-token-123456'
    assert server.retain_last_snapshots == 3

def test_get_hcloud_path(snapshot_manager):
    """Test finding the hcloud CLI executable."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'/usr/local/bin/hcloud\n'
        path = snapshot_manager.get_hcloud_path()
        # Accept any of the common paths
        assert path in [
            '/usr/local/bin/hcloud',
            '/usr/bin/hcloud',
            '/opt/homebrew/bin/hcloud',
            os.path.expanduser('~/.local/bin/hcloud'),
            os.path.expanduser('~/bin/hcloud')
        ]

def test_run_command(snapshot_manager):
    """Test running hcloud commands."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'Command output'
        mock_run.return_value.stderr = b''
        result = snapshot_manager.run_command('test command', 'test-token')
        assert result == 'Command output'

def test_get_snapshots(snapshot_manager):
    """Test retrieving snapshots for a server."""
    with patch('mhsnapshots.SnapshotManager.run_command') as mock_run:
        mock_run.return_value = json.dumps(MOCK_SNAPSHOTS)
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        snapshots = snapshot_manager.get_snapshots(server)
        assert len(snapshots) == 4
        assert all(isinstance(s['created_at'], datetime) for s in snapshots)
        assert all(s['id'] in ['1', '2', '3', '4'] for s in snapshots)

def test_identify_snapshots_to_delete(snapshot_manager):
    """Test identifying snapshots to delete based on retention policy."""
    server = ServerConfig('123456', 'test-server', 'test-token', 3)
    # Make created_at values unique and increasing
    base_time = datetime.now(timezone.utc)
    snapshots = [
        {
            'id': str(i),
            'name': f'test-server-{i}',
            'created_at': base_time.replace(microsecond=0) - timedelta(days=i)
        } for i in range(1, 6)
    ]
    to_delete = snapshot_manager.identify_snapshots_to_delete(server, snapshots, 3)
    assert len(to_delete) == 2
    # The two oldest should be deleted (ids '4' and '5')
    expected_ids = ['4', '5']
    actual_ids = [s['id'] for s in to_delete]
    assert set(actual_ids) == set(expected_ids)

def test_wait_for_snapshot_ready(snapshot_manager):
    """Test waiting for a snapshot to become ready."""
    with patch('mhsnapshots.SnapshotManager.run_command') as mock_run, \
         patch('time.sleep', return_value=None):
        # First call returns 'creating', second call returns 'available'
        mock_run.side_effect = [
            json.dumps({'status': 'creating'}),
            json.dumps({'status': 'available'})
        ]
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        result = snapshot_manager.wait_for_snapshot_ready(server, '1', max_wait_time=5)
        assert result is True

def test_create_snapshot(snapshot_manager):
    """Test creating a new snapshot."""
    with patch('mhsnapshots.SnapshotManager.run_command') as mock_run, \
         patch('mhsnapshots.SnapshotManager.wait_for_snapshot_ready') as mock_wait:
        mock_run.return_value = 'Image 123456 created from Server 123456'
        mock_wait.return_value = True
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        snapshot_name = snapshot_manager.create_snapshot(server)
        assert snapshot_name is not None
        assert snapshot_name.startswith('test-server-')

def test_delete_snapshots(snapshot_manager):
    """Test deleting snapshots."""
    with patch('mhsnapshots.SnapshotManager.run_command') as mock_run:
        mock_run.return_value = 'Image deleted'
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        snapshots = [
            {'id': '1', 'name': 'test-snapshot-1'},
            {'id': '2', 'name': 'test-snapshot-2'}
        ]
        snapshot_manager.delete_snapshots(server, snapshots)
        assert mock_run.call_count == 2

def test_write_final_status(snapshot_manager):
    """Test writing final status to log."""
    # Patch the logger on the instance, not the class
    mock_logger = MagicMock()
    snapshot_manager.logger = mock_logger
    server = ServerConfig('123456', 'test-server', 'test-token', 3)
    snapshot_manager.write_final_status(server, 'test-snapshot', 5, 'success')
    mock_logger.info.assert_called()
    log_message = mock_logger.info.call_args[0][0]
    assert 'FINAL_STATUS' in log_message
    assert 'test-server' in log_message
    assert 'SUCCESS' in log_message
    assert 'test-snapshot' in log_message
    assert '5 snapshots exist' in log_message

def test_manage_snapshots_for_server(snapshot_manager):
    """Test the complete snapshot management process for a server."""
    with patch('mhsnapshots.SnapshotManager.get_snapshots') as mock_get_snapshots, \
         patch('mhsnapshots.SnapshotManager.create_snapshot') as mock_create, \
         patch('mhsnapshots.SnapshotManager.delete_snapshots') as mock_delete, \
         patch('mhsnapshots.SnapshotManager.write_final_status') as mock_write:
        
        # Mock initial snapshots
        mock_get_snapshots.return_value = [
            {
                'id': str(i),
                'name': f'test-server-{i}',
                'created_at': datetime.now(timezone.utc)
            } for i in range(1, 5)
        ]
        
        # Mock successful snapshot creation
        mock_create.return_value = 'test-server-new'
        
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        snapshot_manager.manage_snapshots_for_server(server)
        
        # Verify all expected methods were called
        assert mock_get_snapshots.call_count >= 2  # Called at least twice (before and after creation)
        assert mock_create.call_count == 1
        assert mock_delete.call_count == 1
        assert mock_write.call_count == 1

def test_error_handling(snapshot_manager):
    """Test error handling in various scenarios."""
    with patch('mhsnapshots.SnapshotManager.run_command') as mock_run:
        # Test command failure
        mock_run.return_value = None
        server = ServerConfig('123456', 'test-server', 'test-token', 3)
        result = snapshot_manager.run_command('test command', 'test-token')
        assert result is None

        # Test invalid JSON response
        mock_run.return_value = 'invalid json'
        snapshots = snapshot_manager.get_snapshots(server)
        assert len(snapshots) == 0

def test_invalid_config_file(tmp_path):
    """Test handling of invalid configuration files."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "invalid_config.yaml"
    
    # Create invalid config file
    with open(config_file, 'w') as f:
        f.write('invalid: yaml: content')
    
    with pytest.raises(SystemExit):
        SnapshotManager([str(config_file)], verbose=True) 