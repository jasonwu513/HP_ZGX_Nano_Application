import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from server.config import settings
from server.modules import asr, translation, tts
from server.pipeline import PipelineManager
from server.routes import health
from server.routes.batch import create_batch_router
from server.routes.realtime import create_realtime_router

pipeline = PipelineManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await asr.load()

    import gc, torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    await translation.load()
    await tts.load()
    await pipeline.start()
    yield
    await pipeline.stop()


app = FastAPI(title="Chinese2English Learning Tool", lifespan=lifespan)
app.include_router(health.router)
app.include_router(create_realtime_router(pipeline))
app.include_router(create_batch_router(pipeline))

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )
