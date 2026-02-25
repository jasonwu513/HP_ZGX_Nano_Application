import io
import struct
import wave

from shared.constants import CHANNELS, SAMPLE_RATE, SAMPLE_WIDTH


def encode_wav(pcm_data: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def decode_wav(wav_bytes: bytes) -> tuple[bytes, int]:
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        pcm_data = wf.readframes(wf.getnframes())
        sample_rate = wf.getframerate()
    return pcm_data, sample_rate


def pcm_to_float(pcm_data: bytes) -> list[float]:
    n_samples = len(pcm_data) // SAMPLE_WIDTH
    samples = struct.unpack(f"<{n_samples}h", pcm_data)
    return [s / 32768.0 for s in samples]
