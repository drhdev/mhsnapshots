import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import log2telegram

@pytest.fixture(autouse=True)
def patch_env(monkeypatch, tmp_path):
    # Patch environment variables for Telegram
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'dummy_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'dummy_chat_id')
    # Patch log file path to a temp file
    log_dir = tmp_path / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'mhsnapshots.log'
    monkeypatch.setattr(log2telegram, 'LOG_FILE_PATH', str(log_file))
    monkeypatch.setattr(log2telegram, 'LOGS_DIR', str(log_dir))
    monkeypatch.setattr(log2telegram, 'PROJECT_ROOT', str(tmp_path))
    yield log_file

def test_format_message_valid():
    raw = (
        'FINAL_STATUS | mhsnapshots.py | example.com | SUCCESS | host | 2024-12-02 13:32:34 | snap-20241202133213 | 3 snapshots exist'
    )
    formatted = log2telegram.format_message(raw)
    assert '*FINAL_STATUS*' in formatted
    assert '*Script:* `mhsnapshots.py`' in formatted
    assert '*Status:* `SUCCESS`' in formatted
    assert '*Total Snapshots:* `3 snapshots exist`' in formatted

def test_format_message_invalid():
    raw = 'FINAL_STATUS | incomplete | entry'
    mock_logger = MagicMock()
    formatted = log2telegram.format_message(raw, logger=mock_logger)
    assert formatted == raw
    mock_logger.warning.assert_called()

def test_process_log_sends_telegram(monkeypatch, patch_env):
    log_file = patch_env
    # Write a valid FINAL_STATUS entry
    log_line = '2024-12-02 13:32:34,000 - INFO - FINAL_STATUS | mhsnapshots.py | example.com | SUCCESS | host | 2024-12-02 13:32:34 | snap-20241202133213 | 3 snapshots exist\n'
    log_file.write_text(log_line)
    sent_messages = []
    def fake_send_telegram_message(msg, **kwargs):
        sent_messages.append(msg)
        return True
    monkeypatch.setattr(log2telegram, 'send_telegram_message', fake_send_telegram_message)
    log2telegram.logger = MagicMock()
    log2telegram.process_log(delay_between_messages=0)
    assert len(sent_messages) == 1
    assert 'FINAL_STATUS' in sent_messages[0]

def test_process_log_no_final_status(monkeypatch, patch_env):
    log_file = patch_env
    log_file.write_text('2024-12-02 13:32:34,000 - INFO - Some other log entry\n')
    monkeypatch.setattr(log2telegram, 'send_telegram_message', lambda msg, **kwargs: False)
    log2telegram.logger = MagicMock()
    log2telegram.process_log(delay_between_messages=0)
    # No messages should be sent
    log2telegram.logger.info.assert_any_call('No FINAL_STATUS entries detected to send.')

def test_process_log_multiple_entries(monkeypatch, patch_env):
    log_file = patch_env
    log_lines = [
        '2024-12-02 13:32:34,000 - INFO - FINAL_STATUS | mhsnapshots.py | server1 | SUCCESS | host | 2024-12-02 13:32:34 | snap1 | 2 snapshots exist',
        '2024-12-02 13:32:35,000 - INFO - FINAL_STATUS | mhsnapshots.py | server2 | FAILURE | host | 2024-12-02 13:32:35 | snap2 | 1 snapshots exist',
    ]
    log_file.write_text('\n'.join(log_lines) + '\n')
    sent = []
    monkeypatch.setattr(log2telegram, 'send_telegram_message', lambda msg, **kwargs: sent.append(msg) or True)
    monkeypatch.setattr(log2telegram, 'time', MagicMock())
    log2telegram.logger = MagicMock()
    log2telegram.process_log(delay_between_messages=0)
    assert len(sent) == 2
    assert 'server1' in sent[0]
    assert 'server2' in sent[1]

def test_process_log_delay(monkeypatch, patch_env):
    log_file = patch_env
    log_lines = [
        '2024-12-02 13:32:34,000 - INFO - FINAL_STATUS | mhsnapshots.py | server1 | SUCCESS | host | 2024-12-02 13:32:34 | snap1 | 2 snapshots exist',
        '2024-12-02 13:32:35,000 - INFO - FINAL_STATUS | mhsnapshots.py | server2 | FAILURE | host | 2024-12-02 13:32:35 | snap2 | 1 snapshots exist',
    ]
    log_file.write_text('\n'.join(log_lines) + '\n')
    monkeypatch.setattr(log2telegram, 'send_telegram_message', lambda msg, **kwargs: True)
    sleep_calls = []
    monkeypatch.setattr(log2telegram.time, 'sleep', lambda s: sleep_calls.append(s))
    log2telegram.logger = MagicMock()
    log2telegram.process_log(delay_between_messages=5)
    # Should sleep once between two messages
    assert sleep_calls == [5]

def test_process_log_missing_file(monkeypatch, patch_env):
    log_file = patch_env
    if log_file.exists():
        log_file.unlink()  # Remove the file if it exists
    log2telegram.logger = MagicMock()
    log2telegram.process_log(delay_between_messages=0)
    log2telegram.logger.error.assert_any_call(f"Log file '{log2telegram.LOG_FILE_PATH}' does not exist.")

def test_send_telegram_message_success(monkeypatch):
    # Patch requests.post to simulate success
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'dummy_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'dummy_chat_id')
    monkeypatch.setattr(log2telegram, 'TELEGRAM_API_URL', 'http://fakeurl')
    monkeypatch.setattr(log2telegram, 'logger', MagicMock())
    class FakeResp:
        status_code = 200
        text = 'ok'
    monkeypatch.setattr(log2telegram.requests, 'post', lambda *a, **k: FakeResp())
    result = log2telegram.send_telegram_message('test message')
    assert result is True

def test_send_telegram_message_failure(monkeypatch):
    # Patch requests.post to simulate failure
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'dummy_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'dummy_chat_id')
    monkeypatch.setattr(log2telegram, 'TELEGRAM_API_URL', 'http://fakeurl')
    monkeypatch.setattr(log2telegram, 'logger', MagicMock())
    class FakeResp:
        status_code = 400
        text = 'fail'
    monkeypatch.setattr(log2telegram.requests, 'post', lambda *a, **k: FakeResp())
    result = log2telegram.send_telegram_message('test message', retries=2, delay_between_retries=0)
    assert result is False 