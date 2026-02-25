import logging
import queue

import numpy as np
import sounddevice as sd

from shared.constants import SAMPLE_RATE, CHANNELS, FRAME_SIZE

logger = logging.getLogger(__name__)


class AudioCapture:
    def __init__(self, device: int | None = None):
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._muted: bool = False
        self._device = device

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("錄音狀態: %s", status)
        if self._muted:
            return
        self._queue.put(indata.tobytes())

    def start(self):
        self._stream = sd.InputStream(
            device=self._device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=FRAME_SIZE,
            callback=self._callback,
        )
        self._stream.start()
        device_name = sd.query_devices(self._device or sd.default.device[0])["name"]
        logger.info("錄音已啟動 (裝置=%s, SR=%d, frame=%d)", device_name, SAMPLE_RATE, FRAME_SIZE)

    def read_frame(self, timeout: float = 1.0) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def mute(self):
        self._muted = True
        self.drain()
        logger.debug("錄音已靜音（回聲抑制）")

    def unmute(self):
        self.drain()
        self._muted = False
        logger.debug("錄音已恢復")

    def drain(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("錄音已停止")
