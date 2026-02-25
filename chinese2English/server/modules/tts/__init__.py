"""TTS dispatch layer — public API stays the same regardless of backend."""

import logging
from collections.abc import AsyncIterator

from server.config import settings
from ._base import TTSBackend

logger = logging.getLogger(__name__)

_backend: TTSBackend | None = None


def _create_backend() -> TTSBackend:
    name = settings.tts_backend
    if name == "piper":
        from ._piper import PiperBackend

        return PiperBackend()
    if name == "edge":
        from ._edge import EdgeBackend

        return EdgeBackend()
    if name == "cosyvoice":
        from ._cosyvoice import CosyVoiceBackend

        return CosyVoiceBackend()
    if name == "none":
        from ._none import NoneBackend

        return NoneBackend()
    raise ValueError(f"Unknown TTS backend: {name!r}")


async def load() -> None:
    global _backend
    _backend = _create_backend()
    logger.info("TTS backend: %s", settings.tts_backend)
    await _backend.load()


async def synthesize(text: str) -> AsyncIterator[bytes]:
    if _backend is None:
        raise RuntimeError("TTS not loaded — call load() first")
    async for chunk in _backend.synthesize(text):
        yield chunk


async def synthesize_full(text: str) -> bytes:
    if _backend is None:
        raise RuntimeError("TTS not loaded — call load() first")
    return await _backend.synthesize_full(text)
