import enum
import logging
import struct
import time

from shared.constants import TRAILING_SILENCE_FRAMES, VAD_SPEAKING_THRESHOLD

logger = logging.getLogger(__name__)


class VADState(enum.Enum):
    IDLE = "idle"
    SPEAKING = "speaking"
    TRAILING_SILENCE = "trailing_silence"
    SEGMENT_READY = "segment_ready"


class VADProcessor:
    def __init__(self, energy_threshold: int = 500):
        self._energy_threshold = energy_threshold
        self._state = VADState.IDLE
        self._voiced_count = 0
        self._silence_count = 0
        self._audio_buffer: list[bytes] = []
        self._segment_start_time: float = 0.0
        self._last_segment_start_time: float = 0.0

    def _detect_voice(self, frame: bytes) -> bool:
        n_samples = len(frame) // 2
        samples = struct.unpack(f"<{n_samples}h", frame)
        energy = sum(abs(s) for s in samples) / n_samples
        logger.debug("能量: %.0f", energy)
        return energy > self._energy_threshold

    def process_frame(self, frame: bytes) -> VADState:
        is_voiced = self._detect_voice(frame)

        if self._state == VADState.IDLE:
            if is_voiced:
                self._voiced_count += 1
                self._audio_buffer.append(frame)
                if self._voiced_count >= VAD_SPEAKING_THRESHOLD:
                    self._segment_start_time = time.monotonic()
                    self._state = VADState.SPEAKING
                    logger.debug("狀態: IDLE → SPEAKING")
            else:
                self._voiced_count = 0
                self._audio_buffer.clear()

        elif self._state == VADState.SPEAKING:
            self._audio_buffer.append(frame)
            if not is_voiced:
                self._silence_count = 1
                self._state = VADState.TRAILING_SILENCE

        elif self._state == VADState.TRAILING_SILENCE:
            self._audio_buffer.append(frame)
            if is_voiced:
                self._silence_count = 0
                self._state = VADState.SPEAKING
                logger.debug("狀態: TRAILING_SILENCE → SPEAKING")
            else:
                self._silence_count += 1
                if self._silence_count >= TRAILING_SILENCE_FRAMES:
                    self._state = VADState.SEGMENT_READY
                    logger.debug("狀態: TRAILING_SILENCE → SEGMENT_READY")

        return self._state

    def get_segment(self) -> bytes:
        self._last_segment_start_time = self._segment_start_time
        segment = b"".join(self._audio_buffer)
        self.reset()
        return segment

    def get_segment_start_time(self) -> float:
        return self._last_segment_start_time

    def reset(self):
        self._state = VADState.IDLE
        self._voiced_count = 0
        self._silence_count = 0
        self._audio_buffer.clear()
