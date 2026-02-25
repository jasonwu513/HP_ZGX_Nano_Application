import logging
import queue
import subprocess
import threading

from client.config import client_settings

logger = logging.getLogger(__name__)


class AudioCapture:
    def __init__(self):
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None

    def start(self):
        self._running = True
        frame_bytes = client_settings.frame_size * client_settings.channels * 2  # int16 = 2 bytes

        self._proc = subprocess.Popen(
            [
                "pw-cat", "--record",
                "--rate", str(client_settings.sample_rate),
                "--channels", str(client_settings.channels),
                "--format", "s16",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self._thread = threading.Thread(
            target=self._capture_loop, args=(frame_bytes,), daemon=True
        )
        self._thread.start()
        logger.info("音訊擷取已啟動 (pw-cat, rate=%d, frame=%d)",
                     client_settings.sample_rate, client_settings.frame_size)

    def _capture_loop(self, frame_bytes: int):
        while self._running and self._proc and self._proc.poll() is None:
            try:
                data = self._proc.stdout.read(frame_bytes)
                if not data:
                    break
                if len(data) == frame_bytes:
                    self._queue.put(data)
            except Exception as e:
                if self._running:
                    logger.error("音訊擷取錯誤: %s", e)
                break

    def drain(self):
        """清空錄音緩衝區，丟棄所有已錄製的 frame。"""
        dropped = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        if dropped:
            logger.debug("已丟棄 %d 個緩衝 frame（迴音抑制）", dropped)

    def read_frame(self, timeout: float = 1.0) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self._running = False
        if self._proc:
            self._proc.terminate()
            self._proc.wait()
        logger.info("音訊擷取已停止")
