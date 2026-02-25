import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.pipeline import PipelineManager

logger = logging.getLogger(__name__)

router = APIRouter()


def create_realtime_router(pipeline: PipelineManager) -> APIRouter:
    rt_router = APIRouter()

    @rt_router.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        logger.info("WebSocket 連線已建立")

        try:
            while True:
                audio_bytes = await ws.receive_bytes()
                logger.debug("收到音訊資料: %d bytes", len(audio_bytes))

                try:
                    t0 = time.perf_counter()
                    transcript, english, chunks = await pipeline.process_realtime(audio_bytes)
                    t1 = time.perf_counter()
                    logger.info("Pipeline 完成 (%.2fs), 回傳 %d audio chunks", t1 - t0, len(chunks))

                    for chunk in chunks:
                        await ws.send_bytes(chunk)

                    await ws.send_text(
                        f"EOU|{transcript}|{english}"
                    )
                    logger.debug("已送出 EOU 訊息")
                except Exception as e:
                    logger.error("Pipeline 處理失敗: %s", e, exc_info=True)
                    await ws.send_text(f"ERROR|{e}")

        except WebSocketDisconnect:
            logger.info("WebSocket 連線已斷開")

    return rt_router
