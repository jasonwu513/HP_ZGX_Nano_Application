import io
import logging
import wave

import numpy as np
import sounddevice as sd

from edge.config import settings

logger = logging.getLogger(__name__)


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """簡易線性插值 resample。"""
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    n_samples = int(len(audio) * ratio)
    indices = np.arange(n_samples) / ratio
    indices = np.clip(indices, 0, len(audio) - 1)
    idx_floor = indices.astype(np.int64)
    idx_ceil = np.minimum(idx_floor + 1, len(audio) - 1)
    frac = (indices - idx_floor).astype(np.float32)
    return audio[idx_floor] * (1 - frac) + audio[idx_ceil] * frac


class AudioPlayer:
    def play_wav_bytes(self, wav_bytes: bytes):
        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                pcm = wf.readframes(wf.getnframes())

            audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels)

            device = settings.audio_output_device
            # 查詢裝置支援的 sample rate，必要時 resample
            dev_info = sd.query_devices(device, kind="output")
            dev_sr = int(dev_info["default_samplerate"])
            if sample_rate != dev_sr:
                logger.info("Resample %d → %d Hz (裝置: %s)", sample_rate, dev_sr, dev_info["name"])
                audio = _resample(audio, sample_rate, dev_sr)
                sample_rate = dev_sr

            sd.play(audio, samplerate=sample_rate, device=device)
            sd.wait()
        except Exception as e:
            logger.error("播放失敗: %s", e)
