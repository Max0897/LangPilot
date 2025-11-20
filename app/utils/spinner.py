import itertools
import sys
import threading
import time
from typing import Optional


class Spinner:
    """简单命令行旋转指示器，提示模型正在响应。"""

    def __init__(self, message: str = "🤖 正在等待模型响应，请稍候...", interval: float = 0.15):
        self.message = message
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _animate(self) -> None:
        for frame in itertools.cycle("|/-\\"):
            if self._stop_event.is_set():
                break
            sys.stdout.write(f"\r{self.message} {frame}")
            sys.stdout.flush()
            time.sleep(self.interval)
        sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")
        sys.stdout.flush()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None


__all__ = ["Spinner"]
