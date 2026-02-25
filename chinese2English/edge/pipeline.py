import logging
import struct
import time

import opencc

from shared.constants import SAMPLE_RATE, FRAME_SIZE
from shared.audio_utils import encode_wav
from edge.config import settings
from edge.audio_capture import AudioCapture
from edge.audio_player import AudioPlayer
from edge.vad_processor import VADProcessor, VADState
from edge.modules import asr, translation, tts
from edge.srt_writer import SRTWriter
from shared.audio_saver import AudioSaver

logger = logging.getLogger(__name__)


def run():
    capture = AudioCapture(device=settings.audio_device)
    player = AudioPlayer()
    vad = VADProcessor(energy_threshold=settings.vad_energy_threshold)
    s2t_converter = opencc.OpenCC("s2t")

    # SRT 字幕
    srt: SRTWriter | None = None
    if settings.srt_enabled:
        srt = SRTWriter(output_dir=settings.srt_output_dir)
        srt.start_session(time.monotonic())

    # Audio saving
    audio_saver: AudioSaver | None = None
    if settings.audio_save_enabled:
        audio_saver = AudioSaver(output_dir=settings.audio_save_dir, fmt=settings.audio_save_format)
        audio_saver.start_session()

    # 說話者辨識（條件載入）
    diarize_mod = None
    if settings.diarize_enabled:
        from edge.modules import diarization as diarize_mod

    min_segment_samples = int(settings.min_segment_duration * SAMPLE_RATE) * 2  # bytes

    capture.start()
    logger.info("Pipeline 已啟動，開始聆聽...")

    try:
        while True:
            frame = capture.read_frame()
            if frame is None:
                continue

            state = vad.process_frame(frame)
            if state != VADState.SEGMENT_READY:
                continue

            pcm_segment = vad.get_segment()
            segment_start_time = vad.get_segment_start_time()

            # 過濾過短片段
            if len(pcm_segment) < min_segment_samples:
                logger.debug("片段過短 (%d bytes)，跳過", len(pcm_segment))
                continue

            # 過濾低能量片段
            n_samples = len(pcm_segment) // 2
            samples = struct.unpack(f"<{n_samples}h", pcm_segment)
            avg_energy = sum(abs(s) for s in samples) / n_samples
            if avg_energy < settings.vad_energy_threshold:
                logger.debug("片段能量過低 (%.0f)，跳過", avg_energy)
                continue

            wav_bytes = encode_wav(pcm_segment)
            duration = len(pcm_segment) / 2 / SAMPLE_RATE
            logger.info("--- 偵測到語音片段 (%.1fs) ---", duration)

            t0 = time.perf_counter()

            # 說話者辨識
            speaker_label = None
            if diarize_mod is not None:
                speaker_label = diarize_mod.identify(pcm_segment)

            # ASR + 簡轉繁
            chinese_text = asr.transcribe(wav_bytes)
            if not chinese_text:
                logger.info("ASR 無辨識結果，跳過")
                continue
            chinese_text = s2t_converter.convert(chinese_text)

            # 翻譯
            english_text = translation.translate(chinese_text)
            if not english_text:
                logger.info("翻譯無結果，跳過")
                continue

            total_elapsed = time.perf_counter() - t0

            # SRT 寫入
            segment_end_time = segment_start_time + duration
            if srt is not None:
                srt.write_entry(
                    segment_start_time,
                    segment_end_time,
                    chinese_text,
                    english_text,
                    speaker=speaker_label,
                )

            # Console 輸出
            speaker_prefix = f"[{speaker_label}] " if speaker_label else ""
            print(f"\n{speaker_prefix}中文: {chinese_text}")
            print(f"{speaker_prefix}英文: {english_text}")
            print(f"(處理耗時: {total_elapsed:.1f}s)")

            # TTS + 播放（靜音錄音以抑制回聲）
            audio_wav = tts.synthesize(english_text)
            if audio_saver is not None:
                audio_saver.save_pair(wav_bytes, audio_wav)
            capture.mute()
            player.play_wav_bytes(audio_wav)
            capture.unmute()
            vad.reset()

    except KeyboardInterrupt:
        logger.info("收到中斷訊號，停止中...")
    finally:
        if srt is not None:
            srt.close()
        capture.stop()
