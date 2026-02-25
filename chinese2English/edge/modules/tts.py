import io
import logging
import time
import wave
from pathlib import Path

from edge.config import settings

logger = logging.getLogger(__name__)

_voice = None


def _resolve_model_path(voice_name: str) -> Path:
    p = Path(voice_name)
    if p.is_absolute() and p.exists():
        return p
    if settings.piper_data_dir:
        candidate = Path(settings.piper_data_dir) / f"{voice_name}.onnx"
        if candidate.exists():
            return candidate
    return p


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def load():
    global _voice
    from piper import PiperVoice

    model_path = _resolve_model_path(settings.piper_voice)
    logger.info("載入 Piper 語音模型: %s ...", model_path)
    _voice = PiperVoice.load(str(model_path))
    logger.info("Piper 語音模型載入完成")


def _build_syn_config():
    from piper.config import SynthesisConfig
    return SynthesisConfig(
        length_scale=settings.piper_length_scale,
        noise_scale=settings.piper_noise_scale,
        noise_w_scale=settings.piper_noise_w,
    )


def synthesize(text: str) -> bytes:
    if _voice is None:
        raise RuntimeError("Piper 語音模型未載入，請先呼叫 load()")

    syn_config = _build_syn_config()

    t0 = time.perf_counter()
    all_pcm = b""
    for chunk in _voice.synthesize(text, syn_config=syn_config):
        all_pcm += chunk.audio_int16_bytes
    wav_bytes = _pcm_to_wav(all_pcm, _voice.config.sample_rate)
    elapsed = time.perf_counter() - t0

    duration = len(all_pcm) / 2 / _voice.config.sample_rate
    rtf = elapsed / duration if duration > 0 else 0
    logger.info("TTS: %.2fs 音訊, %.2fs 處理, RTF=%.2f", duration, elapsed, rtf)
    return wav_bytes
