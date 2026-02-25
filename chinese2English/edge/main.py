import logging
import sys

from edge.config import settings


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    from edge.modules import asr, translation, tts

    import sounddevice as sd
    logger.info("可用音訊裝置:\n%s", sd.query_devices())
    if settings.audio_device is not None:
        logger.info("已指定裝置索引: %d", settings.audio_device)
    else:
        logger.info("使用系統預設輸入裝置")

    print("載入模型中...")

    logger.info("載入 ASR 模型...")
    asr.load()

    logger.info("載入翻譯模型...")
    translation.load()

    logger.info("載入 TTS 模型...")
    tts.load()

    if settings.diarize_enabled:
        from edge.modules import diarization
        logger.info("載入說話者辨識模型...")
        diarization.load()

    print("模型載入完成，開始聆聽...")
    print("請對著麥克風說中文，按 Ctrl+C 停止。\n")

    from edge.pipeline import run
    run()


if __name__ == "__main__":
    main()
