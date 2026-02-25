import asyncio
import io
import logging
import wave
from collections.abc import AsyncIterator

from server.config import settings
from ._base import TTSBackend

logger = logging.getLogger(__name__)


class EdgeBackend(TTSBackend):
    def __init__(self) -> None:
        self._voice = settings.edge_tts_voice
        self._ready = False

    async def load(self) -> None:
        try:
            import edge_tts  # noqa: F401

            self._ready = True
            logger.info("edge-tts 後端就緒，語音: %s", self._voice)
        except ImportError:
            logger.warning(
                "edge-tts 未安裝，TTS 模組將無法使用。"
                "請執行: pip install edge-tts"
            )

    async def _communicate(self, text: str) -> bytes:
        """Call edge-tts and return raw MP3 bytes."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self._voice)
        mp3_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_chunks.append(chunk["data"])
        return b"".join(mp3_chunks)

    @staticmethod
    def _mp3_to_wav(mp3_data: bytes) -> bytes:
        from pydub import AudioSegment

        seg = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        seg = seg.set_channels(1).set_sample_width(2)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(seg.frame_rate)
            wf.writeframes(seg.raw_data)
        return buf.getvalue()

    async def synthesize_full(self, text: str) -> bytes:
        if not self._ready:
            raise RuntimeError("edge-tts 未載入")
        mp3_data = await self._communicate(text)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._mp3_to_wav, mp3_data)

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        wav_bytes = await self.synthesize_full(text)
        yield wav_bytes
