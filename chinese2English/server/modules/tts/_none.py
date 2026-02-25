import logging
from collections.abc import AsyncIterator

from ._base import TTSBackend

logger = logging.getLogger(__name__)


class NoneBackend(TTSBackend):
    async def load(self) -> None:
        logger.info("TTS backend set to 'none' — TTS is disabled.")

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        raise RuntimeError("TTS is disabled (backend='none')")
        yield  # pragma: no cover – make this a generator

    async def synthesize_full(self, text: str) -> bytes:
        raise RuntimeError("TTS is disabled (backend='none')")
