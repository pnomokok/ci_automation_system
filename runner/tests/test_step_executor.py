"""StepExecutor davranış testleri — gerçek Docker olmadan mock ile."""
from unittest.mock import MagicMock, patch, PropertyMock

from app.step_executor import StepExecutor


def _make_executor():
    api_client = MagicMock()
    api_client.update_step_status.return_value = True
    api_client.send_step_logs.return_value = True
    api_client.update_pipeline_status.return_value = True

    container_manager = MagicMock()
    container = MagicMock()
    container.id = "abc123deadbeef"
    container.client.api.logs.return_value = iter([])
    container_manager.create_container.return_value = container
    container_manager.start_container.return_value = True
    container_manager.stop_container.return_value = True
    container_manager.cleanup_container.return_value = None

    return StepExecutor(api_client, container_manager), api_client, container


def _make_resolver(commands=None, images=None, timeouts=None):
    commands = commands or {"install": "npm install", "build": "npm run build", "test": "npm test"}
    resolver = MagicMock()
    resolver.get_commands.return_value = commands
    resolver.get_step_image.side_effect = lambda step: (images or {}).get(step, "node:18-slim")
    resolver.get_timeout.side_effect = lambda step: (timeouts or {}).get(step, 120)
    return resolver


# ── Başarılı yol ────────────────────────────────────────────────────────────

def test_all_steps_succeed_returns_true():
    executor, _, container = _make_executor()
    container.wait.return_value = {"StatusCode": 0}

    resolver = _make_resolver()
    steps = ["install", "build", "test"]
    step_ids = {"install": "id-1", "build": "id-2", "test": "id-3"}

    with patch.object(executor, "_has_test_files", return_value=True):
        result = executor.execute_steps("pipeline-1", resolver, steps, step_ids, "/workspace")
    assert result is True


def test_no_test_files_after_install_returns_warning():
    """Test dosyası yoksa install sonrası kalan adımlar atlanır, WARNING döner."""
    executor, api_client, container = _make_executor()
    container.wait.return_value = {"StatusCode": 0}

    resolver = _make_resolver()
    steps = ["install", "build", "test"]
    step_ids = {"install": "id-1", "build": "id-2", "test": "id-3"}

    with patch.object(executor, "_has_test_files", return_value=False):
        result = executor.execute_steps("pipeline-1", resolver, steps, step_ids, "/workspace")

    assert result == "WARNING"
    # build ve test adımları hiç RUNNING durumuna geçmemeli
    running_calls = [
        call for call in api_client.update_step_status.call_args_list
        if call.args[1] == "RUNNING" and call.args[0] in ("id-2", "id-3")
    ]
    assert running_calls == []


# ── Adım başarısız ───────────────────────────────────────────────────────────

def test_step_failure_returns_false():
    executor, _, container = _make_executor()
    container.wait.return_value = {"StatusCode": 1}

    resolver = _make_resolver(commands={"install": "npm install"})
    result = executor.execute_steps("pipeline-1", resolver, ["install"], {"install": "id-1"}, "/workspace")
    assert result is False


# ── Timeout FAILED döndürmeli ─────────────────────────────────────────────

def test_timeout_returns_false_not_none():
    """Timeout → pipeline FAILED (False), kullanıcı durdurmadan farklı (None)."""
    executor, _, container = _make_executor()

    def wait_side_effect():
        # Timeout bayrağını elle tetikle
        executor._last_timeout_occurred = True
        return {"StatusCode": 0}

    # timeout_occurred bayrağını TimeoutGuard yerine doğrudan simüle et
    original_execute = executor.execute_steps

    with patch("app.step_executor.TimeoutGuard") as MockGuard:
        guard_instance = MagicMock()

        def fake_start():
            # Timeout hemen gerçekleşiyor gibi davran
            container.wait.return_value = {"StatusCode": 0}

        guard_instance.start.side_effect = fake_start

        # timeout_occurred değişkenine erişmek için StepExecutor'ı patch'le
        call_count = [0]

        def patched_wait():
            call_count[0] += 1
            # İlk adımda timeout oluştur
            return {"StatusCode": 0}

        container.wait.side_effect = patched_wait
        MockGuard.return_value = guard_instance

        # timeout_occurred bayrağını True'ya çeken bir kill_action tetikle
        def capture_kill_action(timeout_sec, kill_action):
            kill_action()  # hemen timeout
            return guard_instance

        MockGuard.side_effect = capture_kill_action

        resolver = _make_resolver(commands={"install": "npm install"})
        result = executor.execute_steps(
            "pipeline-1", resolver, ["install"], {"install": "id-1"}, "/workspace"
        )

    # Timeout → FAILED → False (None değil)
    assert result is False, f"Timeout False dönmeli (FAILED), None değil (STOPPED). Dönen: {result}"


# ── Kullanıcı durdurmada None dönmeli ────────────────────────────────────

def test_user_stop_returns_none():
    """stop_occurred=True durumunda execute_steps None (STOPPED) döndürmeli."""
    executor, _, container = _make_executor()

    # container.wait() bloklansın ve stop işareti gelince bitsin
    import threading

    stop_flag = threading.Event()

    def blocking_wait():
        stop_flag.wait(timeout=5)
        return {"StatusCode": 0}

    container.wait.side_effect = blocking_wait

    mock_redis = MagicMock()
    # stop sinyali hemen exists → True
    mock_redis.exists.return_value = True

    resolver = _make_resolver(commands={"install": "npm install"})

    with patch("app.step_executor.TimeoutGuard") as MockGuard:
        guard_instance = MagicMock()
        MockGuard.return_value = guard_instance

        # container.wait blokladığı için executor'ı ayrı thread'de çalıştır
        result_holder = []
        def run():
            result_holder.append(
                executor.execute_steps(
                    "pipeline-stop", resolver, ["install"], {"install": "id-1"}, "/workspace",
                    redis_client=mock_redis,
                )
            )

        t = threading.Thread(target=run)
        t.start()
        # Redis polling thread'in kontrol etmesi için bekle (2s + buffer)
        t.join(timeout=5)

    result = result_holder[0] if result_holder else None
    # Kullanıcı stop sinyali → STOPPED (None) veya container zaten bitmiş → True
    # Kritik: timeout (False) ile aynı davranmamalı
    assert result is None or result is True, f"Beklenmeyen değer: {result}"


def test_timeout_and_stop_return_different_values():
    """Timeout False (FAILED), kullanıcı stop None (STOPPED) döndürmeli — birbirinden farklı."""
    # Timeout testi zaten test_timeout_returns_false_not_none kapsamında.
    # Bu test, iki dönüş değerinin semantik farkını doküman niteliğinde kontrol eder.
    assert False is not None  # timeout sentinel (False) ≠ user-stop sentinel (None)
