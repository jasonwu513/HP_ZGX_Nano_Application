import asyncio
import io
import logging
import wave
from collections.abc import AsyncIterator
from functools import partial
from pathlib import Path

from server.config import settings
from ._base import TTSBackend

logger = logging.getLogger(__name__)

PIPER_SAMPLE_RATE = 22050


class PiperBackend(TTSBackend):
    def __init__(self) -> None:
        self._voice = None

    async def load(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_voice)

    def _load_voice(self) -> None:
        try:
            from piper import PiperVoice

            model_path = self._resolve_model_path(settings.piper_voice)
            logger.info("載入 Piper 語音模型: %s ...", model_path)
            self._voice = PiperVoice.load(str(model_path))
            logger.info("Piper 語音模型載入完成")
        except ImportError:
            logger.warning(
                "piper-tts 未安裝，TTS 模組將無法使用。"
                "請執行: pip install piper-tts"
            )
        except Exception as e:
            logger.error("Piper 載入失敗: %s", e)

    @staticmethod
    def _resolve_model_path(voice_name: str) -> Path:
        p = Path(voice_name)
        if p.is_absolute() and p.exists():
            return p
        if settings.piper_data_dir:
            candidate = Path(settings.piper_data_dir) / f"{voice_name}.onnx"
            if candidate.exists():
                return candidate
        return p

    @staticmethod
    def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    def _synthesize_full_sync(self, text: str) -> bytes:
        if self._voice is None:
            raise RuntimeError("Piper 語音模型未載入")
        all_pcm = b""
        for chunk in self._voice.synthesize(text):
            all_pcm += chunk.audio_int16_bytes
        return self._pcm_to_wav(all_pcm, self._voice.config.sample_rate)

    def _synthesize_chunks(self, text: str) -> list[bytes]:
        if self._voice is None:
            raise RuntimeError("Piper 語音模型未載入")
        chunks: list[bytes] = []
        sr = self._voice.config.sample_rate
        for audio_chunk in self._voice.synthesize(text):
            wav_bytes = self._pcm_to_wav(audio_chunk.audio_int16_bytes, sr)
            chunks.append(wav_bytes)
        return chunks

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(
            None, partial(self._synthesize_chunks, text)
        )
        for chunk in chunks:
            yield chunk

    async def synthesize_full(self, text: str) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, partial(self._synthesize_full_sync, text)
        )
