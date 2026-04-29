import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

class TimeoutGuard:
    def __init__(self, timeout_sec: int, kill_action: Callable):
        """
        :param timeout_sec: Timeout in seconds
        :param kill_action: Callable to execute when timeout is reached
        """
        self.timeout_sec = timeout_sec
        self.kill_action = kill_action
        self._timer = None

    def start(self):
        """Starts the timeout watchdog."""
        if self.timeout_sec <= 0:
            return
        
        logger.info(f"Starting timeout guard for {self.timeout_sec} seconds.")
        self._timer = threading.Timer(self.timeout_sec, self._on_timeout)
        self._timer.start()

    def stop(self):
        """Stops the timeout watchdog."""
        if self._timer:
            self._timer.cancel()
            logger.info("Timeout guard stopped.")

    def _on_timeout(self):
        logger.error(f"Timeout of {self.timeout_sec}s exceeded! Executing kill action.")
        try:
            self.kill_action()
        except Exception as e:
            logger.error(f"Error executing kill action on timeout: {e}")
