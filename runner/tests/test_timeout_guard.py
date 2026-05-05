import time

from app.timeout_guard import TimeoutGuard


def test_kill_action_called_on_timeout():
    called = []
    guard = TimeoutGuard(timeout_sec=0.1, kill_action=lambda: called.append(True))
    guard.start()
    time.sleep(0.3)
    assert called, "kill_action should have been called after timeout"


def test_kill_action_not_called_if_stopped_early():
    called = []
    guard = TimeoutGuard(timeout_sec=0.5, kill_action=lambda: called.append(True))
    guard.start()
    time.sleep(0.1)
    guard.stop()
    time.sleep(0.5)
    assert not called, "kill_action should NOT be called after guard is stopped"


def test_zero_timeout_does_not_start():
    called = []
    guard = TimeoutGuard(timeout_sec=0, kill_action=lambda: called.append(True))
    guard.start()
    time.sleep(0.1)
    assert not called


def test_kill_action_exception_does_not_propagate():
    def bad_action():
        raise RuntimeError("boom")

    guard = TimeoutGuard(timeout_sec=0.1, kill_action=bad_action)
    guard.start()
    time.sleep(0.3)
    # No exception should escape the timeout guard
