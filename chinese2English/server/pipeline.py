import asyncio
import logging
import time
from collections.abc import Coroutine
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from pydantic import BaseModel

from server.config import settings
from server.modules import asr, translation, tts
from shared.constants import SAMPLE_RATE

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    REALTIME = 0
    BATCH = 10


class BatchResult(BaseModel):
    segments: list[str]
    direct_translation: str
    child_story: str
    direct_audio: bytes
    story_audio: bytes

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class _QueueItem:
    priority: int
    seq: int
    coro: Coroutine[Any, Any, Any]
    future: asyncio.Future

    def __lt__(self, other: "_QueueItem"):
        return (self.priority, self.seq) < (other.priority, other.seq)


class PipelineManager:
    def __init__(self):
        self._queue: asyncio.PriorityQueue[_QueueItem] = asyncio.PriorityQueue()
        self._seq = 0
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()

    PIPELINE_TIMEOUT = settings.pipeline_timeout

    async def _worker(self):
        while True:
            item = await self._queue.get()
            try:
                result = await asyncio.wait_for(
                    item.coro, timeout=self.PIPELINE_TIMEOUT
                )
                item.future.set_result(result)
            except asyncio.TimeoutError:
                logger.error("Pipeline 逾時 (%ds)，跳過此請求", self.PIPELINE_TIMEOUT)
                item.future.set_exception(
                    TimeoutError(f"Pipeline 處理超過 {self.PIPELINE_TIMEOUT}s")
                )
            except Exception as e:
                item.future.set_exception(e)
            finally:
                self._queue.task_done()

    async def _enqueue(self, coro, priority: Priority):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._seq += 1
        await self._queue.put(_QueueItem(priority, self._seq, coro, future))
        return await future

    async def process_realtime(self, audio_bytes: bytes) -> tuple[str, str, list[bytes]]:
        async def _pipeline():
            duration_sec = len(audio_bytes) / (SAMPLE_RATE * 2)  # 16-bit PCM
            logger.info("Realtime 音訊長度: %.2f 秒", duration_sec)

            t0 = time.perf_counter()

            transcript = await asr.transcribe(audio_bytes)
            t1 = time.perf_counter()
            logger.info("ASR 結果: %s (%.2fs)", transcript, t1 - t0)

            if not transcript.strip():
                return "", "", []

            english = await translation.translate_sentence(transcript)
            t2 = time.perf_counter()
            logger.info("翻譯結果: %s (%.2fs)", english, t2 - t1)

            chunks = []
            try:
                async for chunk in tts.synthesize(english):
                    chunks.append(chunk)
            except RuntimeError:
                logger.warning("TTS 未載入，跳過語音合成")
            t3 = time.perf_counter()
            total = t3 - t0
            rtf = total / duration_sec if duration_sec > 0 else 0
            logger.info("TTS 完成: %d chunks (%.2fs)", len(chunks), t3 - t2)
            logger.info("Pipeline 總計: %.2fs, RTF: %.2f", total, rtf)

            return transcript, english, chunks

        return await self._enqueue(_pipeline(), Priority.REALTIME)

    async def process_batch(self, audio_bytes: bytes) -> BatchResult:
        async def _pipeline():
            duration_sec = len(audio_bytes) / (SAMPLE_RATE * 2)  # 16-bit PCM
            logger.info("Batch 音訊長度: %.2f 秒", duration_sec)

            t0 = time.perf_counter()

            transcript = await asr.transcribe(audio_bytes)
            t1 = time.perf_counter()
            logger.info("批次 ASR 結果: %s (%.2fs)", transcript, t1 - t0)

            segments = [s.strip() for s in transcript.split("。") if s.strip()]
            if not segments:
                segments = [transcript]

            batch_trans = await translation.translate_batch(segments)
            t2 = time.perf_counter()
            logger.info("批次翻譯完成 (%.2fs)", t2 - t1)

            try:
                direct_audio = await tts.synthesize_full(batch_trans.direct_translation)
                t3 = time.perf_counter()
                logger.info("批次 TTS (direct) 完成 (%.2fs)", t3 - t2)

                story_audio = await tts.synthesize_full(batch_trans.child_story)
                t4 = time.perf_counter()
                logger.info("批次 TTS (story) 完成 (%.2fs)", t4 - t3)
            except RuntimeError:
                logger.warning("TTS 未載入，跳過語音合成")
                direct_audio = b""
                story_audio = b""

            total = time.perf_counter() - t0
            rtf = total / duration_sec if duration_sec > 0 else 0
            logger.info("批次 Pipeline 總計: %.2fs, RTF: %.2f", total, rtf)

            return BatchResult(
                segments=segments,
                direct_translation=batch_trans.direct_translation,
                child_story=batch_trans.child_story,
                direct_audio=direct_audio,
                story_audio=story_audio,
            )

        return await self._enqueue(_pipeline(), Priority.BATCH)
