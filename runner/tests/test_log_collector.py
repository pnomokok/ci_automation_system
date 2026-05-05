import time
from unittest.mock import MagicMock

from app.log_collector import LogCollector


def _make_collector():
    api = MagicMock()
    api.send_step_logs = MagicMock(return_value=True)
    return LogCollector(api, "step-123"), api


def test_stop_collecting_flushes_buffered_logs():
    collector, api = _make_collector()
    collector.logs_buffer = ["line 1", "line 2"]
    collector.stop_collecting()
    api.send_step_logs.assert_called_once_with("step-123", ["line 1", "line 2"])


def test_stop_collecting_does_not_call_api_if_buffer_empty():
    collector, api = _make_collector()
    collector.stop_collecting()
    api.send_step_logs.assert_not_called()


def test_flush_clears_buffer():
    collector, api = _make_collector()
    collector.logs_buffer = ["a", "b", "c"]
    collector._flush_logs()
    assert collector.logs_buffer == []


def test_flush_sends_correct_step_id():
    collector, api = _make_collector()
    collector.logs_buffer = ["hello"]
    collector._flush_logs()
    api.send_step_logs.assert_called_once_with("step-123", ["hello"])


def test_batch_flush_when_buffer_reaches_limit():
    collector, api = _make_collector()
    # Fill buffer to batch_size
    for i in range(collector.batch_size):
        with collector._lock:
            collector.logs_buffer.append(f"line {i}")
            if len(collector.logs_buffer) >= collector.batch_size:
                collector._flush_logs()
    api.send_step_logs.assert_called_once()
    assert collector.logs_buffer == []
