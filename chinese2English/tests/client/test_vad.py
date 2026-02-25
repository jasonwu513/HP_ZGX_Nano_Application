import struct
from unittest.mock import patch

import pytest

from client.vad_processor import VADProcessor, VADState
from shared.constants import FRAME_SIZE, TRAILING_SILENCE_FRAMES, VAD_SPEAKING_THRESHOLD


def _make_frame(amplitude: int = 0) -> bytes:
    return struct.pack(f"<{FRAME_SIZE}h", *([amplitude] * FRAME_SIZE))


def _silent_frame() -> bytes:
    return _make_frame(0)


def _voiced_frame() -> bytes:
    return _make_frame(2000)


def _make_vad(voiced_sequence: list[bool]) -> VADProcessor:
    """Create a VADProcessor with _detect_voice returning values from sequence."""
    vad = VADProcessor()
    vad.start()
    it = iter(voiced_sequence)
    vad._detect_voice = lambda _frame: next(it)
    return vad


def test_idle_to_speaking():
    voiced = [True] * VAD_SPEAKING_THRESHOLD
    vad = _make_vad(voiced)

    for _ in range(VAD_SPEAKING_THRESHOLD - 1):
        state = vad.process_frame(_voiced_frame())
        assert state == VADState.IDLE

    state = vad.process_frame(_voiced_frame())
    assert state == VADState.SPEAKING


def test_speaking_to_segment_ready():
    voiced = (
        [True] * VAD_SPEAKING_THRESHOLD
        + [True] * 10
        + [False] * TRAILING_SILENCE_FRAMES
    )
    vad = _make_vad(voiced)

    for _ in range(VAD_SPEAKING_THRESHOLD):
        vad.process_frame(_voiced_frame())

    for _ in range(10):
        vad.process_frame(_voiced_frame())

    for _ in range(TRAILING_SILENCE_FRAMES - 1):
        state = vad.process_frame(_silent_frame())
        assert state == VADState.TRAILING_SILENCE

    state = vad.process_frame(_silent_frame())
    assert state == VADState.SEGMENT_READY


def test_get_segment_resets():
    voiced = (
        [True] * (VAD_SPEAKING_THRESHOLD + 5)
        + [False] * TRAILING_SILENCE_FRAMES
    )
    vad = _make_vad(voiced)

    for _ in range(VAD_SPEAKING_THRESHOLD + 5):
        vad.process_frame(_voiced_frame())

    for _ in range(TRAILING_SILENCE_FRAMES):
        vad.process_frame(_silent_frame())

    segment = vad.get_segment()
    assert len(segment) > 0
    assert vad._state == VADState.IDLE


def test_trailing_silence_back_to_speaking():
    voiced = (
        [True] * VAD_SPEAKING_THRESHOLD
        + [False] * 5
        + [True]
    )
    vad = _make_vad(voiced)

    for _ in range(VAD_SPEAKING_THRESHOLD):
        vad.process_frame(_voiced_frame())

    for _ in range(5):
        vad.process_frame(_silent_frame())

    state = vad.process_frame(_voiced_frame())
    assert state == VADState.SPEAKING
