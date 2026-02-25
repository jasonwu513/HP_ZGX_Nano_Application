import asyncio
import io
import logging
from functools import partial

import librosa
import numpy as np
import torch

from server.config import settings
from shared.constants import SAMPLE_RATE

logger = logging.getLogger(__name__)

_model = None
_gpu_lock = asyncio.Lock()


def _load_model():
    global _model
    from qwen_asr import Qwen3ASRModel

    logger.info("載入 ASR 模型: %s ...", settings.asr_model_id)

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    _model = Qwen3ASRModel.from_pretrained(
        settings.asr_model_id,
        dtype=dtype,
        device_map=device,
        max_inference_batch_size=1,
        max_new_tokens=256,
    )
    logger.info("ASR 模型載入完成")


def _transcribe_sync(audio_bytes: bytes) -> str:
    audio, _ = librosa.load(io.BytesIO(audio_bytes), sr=SAMPLE_RATE)
    audio = audio.astype(np.float32)

    duration_sec = len(audio) / SAMPLE_RATE
    logger.info("ASR 輸入音訊長度: %.2f 秒", duration_sec)

    results = _model.transcribe(audio=(audio, SAMPLE_RATE))
    return results[0].text


async def load():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _load_model)


async def transcribe(audio_bytes: bytes) -> str:
    if _model is None:
        raise RuntimeError("ASR 模型未載入，請先呼叫 load()")

    loop = asyncio.get_running_loop()
    async with _gpu_lock:
        return await loop.run_in_executor(
            None, partial(_transcribe_sync, audio_bytes)
        )
