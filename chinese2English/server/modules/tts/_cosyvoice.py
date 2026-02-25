import asyncio
import io
import logging
import wave
from collections.abc import AsyncIterator
from functools import partial

import torch

from server.config import settings
from ._base import TTSBackend

logger = logging.getLogger(__name__)

TTS_SAMPLE_RATE = 22050  # CosyVoice default output rate


class CosyVoiceBackend(TTSBackend):
    def __init__(self) -> None:
        self._model = None
        self._gpu_lock = asyncio.Lock()

    async def load(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_model)

    def _load_model(self) -> None:
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice2

            logger.info("載入 CosyVoice 模型: %s ...", settings.cosyvoice_model_dir)
            self._model = CosyVoice2(
                settings.cosyvoice_model_dir, load_jit=False, load_trt=False
            )
            logger.info("CosyVoice 模型載入完成")
        except ImportError:
            logger.warning(
                "CosyVoice 未安裝，TTS 模組將無法使用。"
                "請參考 https://github.com/FunAudioLLM/CosyVoice 安裝。"
            )
        except Exception as e:
            logger.error("CosyVoice 載入失敗: %s", e)

    @staticmethod
    def _pcm_to_wav(pcm_tensor: torch.Tensor, sample_rate: int) -> bytes:
        import numpy as np

        audio_np = pcm_tensor.squeeze().cpu().numpy()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio_np * 32767).astype(np.int16).tobytes())
        return buf.getvalue()

    def _synthesize_chunks(self, text: str) -> list[bytes]:
        if self._model is None:
            raise RuntimeError("CosyVoice 模型未載入")
        chunks: list[bytes] = []
        for chunk in self._model.inference_cross_lingual(
            tts_text=text, prompt_speech_16k=None
        ):
            wav_bytes = self._pcm_to_wav(chunk["tts_speech"], TTS_SAMPLE_RATE)
            chunks.append(wav_bytes)
        return chunks

    def _synthesize_full_sync(self, text: str) -> bytes:
        if self._model is None:
            raise RuntimeError("CosyVoice 模型未載入")
        all_audio = []
        for chunk in self._model.inference_cross_lingual(
            tts_text=text, prompt_speech_16k=None
        ):
            all_audio.append(chunk["tts_speech"])
        if not all_audio:
            return b""
        combined = torch.cat(all_audio, dim=-1)
        return self._pcm_to_wav(combined, TTS_SAMPLE_RATE)

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        async with self._gpu_lock:
            chunks = await loop.run_in_executor(
                None, partial(self._synthesize_chunks, text)
            )
        for chunk in chunks:
            yield chunk

    async def synthesize_full(self, text: str) -> bytes:
        loop = asyncio.get_running_loop()
        async with self._gpu_lock:
            return await loop.run_in_executor(
                None, partial(self._synthesize_full_sync, text)
            )
