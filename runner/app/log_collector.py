import logging
import threading

logger = logging.getLogger(__name__)

class LogCollector:
    def __init__(self, api_client, step_id: str):
        self.api_client = api_client
        self.step_id = step_id
        self.batch_size = 50
        self.logs_buffer = []
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker_thread = None

    def start_collecting(self, container):
        """Starts collecting logs from the given container."""
        logger.info(f"Starting log collection for step {self.step_id}")
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._stream_logs, args=(container,))
        self._worker_thread.start()

    def stop_collecting(self):
        """Stops the log collection thread and flushes remaining logs."""
        logger.info(f"Stopping log collection for step {self.step_id}")
        self._stop_event.set()
        if self._worker_thread:
            # wait a short time for the thread to finish naturally after container stops
            self._worker_thread.join(timeout=2)
        self._flush_logs()

    def _stream_logs(self, container):
        try:
            # We use stream=True to get logs as they arrive.
            for log_chunk in container.logs(stream=True, follow=True, stdout=True, stderr=True):
                if self._stop_event.is_set():
                    break
                
                # decode and strip trailing newline
                line = log_chunk.decode('utf-8', errors='replace').rstrip('\r\n')
                
                with self._lock:
                    self.logs_buffer.append(line)
                    if len(self.logs_buffer) >= self.batch_size:
                        self._flush_logs()
        except Exception as e:
            logger.error(f"Error streaming logs for step {self.step_id}: {e}")

    def _flush_logs(self):
        logs_to_send = []
        with self._lock:
            if not self.logs_buffer:
                return
            logs_to_send = list(self.logs_buffer)
            self.logs_buffer.clear()

        # Send to API
        self.api_client.send_step_logs(self.step_id, logs_to_send)
