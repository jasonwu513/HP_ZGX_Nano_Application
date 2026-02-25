import base64
import logging

from fastapi import APIRouter, File, UploadFile

from server.pipeline import PipelineManager

logger = logging.getLogger(__name__)


def create_batch_router(pipeline: PipelineManager) -> APIRouter:
    bt_router = APIRouter()

    @bt_router.post("/batch")
    async def batch_translate(file: UploadFile = File(...)):
        audio_bytes = await file.read()
        logger.info("收到批次音訊: %s (%d bytes)", file.filename, len(audio_bytes))

        result = await pipeline.process_batch(audio_bytes)

        return {
            "segments": result.segments,
            "direct_translation": result.direct_translation,
            "child_story": result.child_story,
            "direct_audio_b64": base64.b64encode(result.direct_audio).decode(),
            "story_audio_b64": base64.b64encode(result.story_audio).decode(),
        }

    return bt_router
