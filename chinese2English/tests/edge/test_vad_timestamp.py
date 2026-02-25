import struct
import time
from unittest.mock import patch

from edge.vad_processor import VADProcessor, VADState
from shared.constants import VAD_SPEAKING_THRESHOLD, TRAILING_SILENCE_FRAMES


def _make_voiced_frame(energy: int = 1000, size: int = 256) -> bytes:
    """產生高能量 frame（被偵測為語音）。"""
    return struct.pack(f"<{size}h", *([energy] * size))


def _make_silent_frame(size: int = 256) -> bytes:
    """產生靜音 frame。"""
    return struct.pack(f"<{size}h", *([0] * size))


class TestSegmentStartTimeRecording:
    def test_idle_to_speaking_records_time(self):
        vad = VADProcessor(energy_threshold=500)
        t_before = time.monotonic()

        # 送入足夠的 voiced frame 觸發 IDLE → SPEAKING
        for _ in range(VAD_SPEAKING_THRESHOLD):
            state = vad.process_frame(_make_voiced_frame())

        t_after = time.monotonic()

        assert state == VADState.SPEAKING
        assert vad._segment_start_time >= t_before
        assert vad._segment_start_time <= t_after

    def test_start_time_set_on_threshold_crossing(self):
        vad = VADProcessor(energy_threshold=500)

        # 送入 threshold - 1 個 frame，還沒到 SPEAKING
        for _ in range(VAD_SPEAKING_THRESHOLD - 1):
            vad.process_frame(_make_voiced_frame())

        assert vad._segment_start_time == 0.0  # 還未設定

        # 第 threshold 個 frame 觸發 SPEAKING
        vad.process_frame(_make_voiced_frame())
        assert vad._segment_start_time > 0.0


class TestGetSegmentStartTime:
    def test_get_segment_start_time_after_get_segment(self):
        vad = VADProcessor(energy_threshold=500)

        # 觸發 SPEAKING
        for _ in range(VAD_SPEAKING_THRESHOLD):
            vad.process_frame(_make_voiced_frame())

        recorded_time = vad._segment_start_time

        # 繼續送入一些 voiced frame
        for _ in range(5):
            vad.process_frame(_make_voiced_frame())

        # 送入足夠靜音觸發 SEGMENT_READY
        for _ in range(TRAILING_SILENCE_FRAMES):
            state = vad.process_frame(_make_silent_frame())

        assert state == VADState.SEGMENT_READY

        # get_segment 後應能取得 start time
        segment = vad.get_segment()
        assert len(segment) > 0
        assert vad.get_segment_start_time() == recorded_time

    def test_start_time_preserved_after_reset(self):
        vad = VADProcessor(energy_threshold=500)

        # 完成一個完整的 segment
        for _ in range(VAD_SPEAKING_THRESHOLD):
            vad.process_frame(_make_voiced_frame())
        for _ in range(5):
            vad.process_frame(_make_voiced_frame())
        for _ in range(TRAILING_SILENCE_FRAMES):
            vad.process_frame(_make_silent_frame())

        vad.get_segment()
        first_time = vad.get_segment_start_time()
        assert first_time > 0

        # reset 後 _last_segment_start_time 仍保留
        assert vad.get_segment_start_time() == first_time

    def test_default_start_time_is_zero(self):
        vad = VADProcessor(energy_threshold=500)
        assert vad.get_segment_start_time() == 0.0
