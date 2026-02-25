import asyncio
import base64
import logging

import httpx

from client.audio_capture import AudioCapture
from client.audio_player import AudioPlayer
from client.config import client_settings
from client.vad_processor import VADProcessor, VADState
from shared.audio_utils import encode_wav
from shared.audio_saver import AudioSaver

logger = logging.getLogger(__name__)


async def run_batch():
    capture = AudioCapture()
    vad = VADProcessor()
    player = AudioPlayer()

    # Audio saving
    audio_saver: AudioSaver | None = None
    if client_settings.audio_save_enabled:
        audio_saver = AudioSaver(output_dir=client_settings.audio_save_dir, fmt=client_settings.audio_save_format)
        audio_saver.start_session()

    capture.start()
    vad.start()

    all_pcm = bytearray()

    print("=== 批次錄音模式 ===")
    print("開始錄音中... 按 Enter 停止錄音並送出翻譯")

    stop_event = asyncio.Event()

    async def wait_for_enter():
        await asyncio.to_thread(input)
        stop_event.set()

    enter_task = asyncio.create_task(wait_for_enter())

    while not stop_event.is_set():
        frame = await asyncio.to_thread(capture.read_frame, 0.3)
        if frame is None:
            continue

        state = vad.process_frame(frame)

        if state in (VADState.SPEAKING, VADState.TRAILING_SILENCE):
            all_pcm.extend(frame)
        elif state == VADState.SEGMENT_READY:
            segment = vad.get_segment()
            all_pcm.extend(segment)

    enter_task.cancel()
    capture.stop()

    if not all_pcm:
        print("未偵測到任何語音")
        return

    wav_data = encode_wav(bytes(all_pcm))
    input_index = None
    if audio_saver is not None:
        audio_saver.save_input(wav_data)
        input_index = audio_saver.current_index
    print(f"錄音完成，共 {len(wav_data)} bytes，正在上傳...")

    batch_url = f"{client_settings.server_http_url}/batch"
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                batch_url,
                files={"file": ("recording.wav", wav_data, "audio/wav")},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("批次翻譯失敗: %s", e)
            print(f"錯誤: {e}")
            return

    print("\n=== 原文段落 ===")
    for seg in data["segments"]:
        print(f"  {seg}")

    print(f"\n=== 直譯 ===\n{data['direct_translation']}")
    print(f"\n=== 兒童故事版 ===\n{data['child_story']}")

    print("\n播放直譯音訊...")
    direct_audio = base64.b64decode(data["direct_audio_b64"])
    if audio_saver is not None and input_index is not None:
        audio_saver.save_output(direct_audio, index=input_index, label="output_direct")
    await asyncio.to_thread(player.play_wav_bytes, direct_audio)

    print("播放兒童故事音訊...")
    story_audio = base64.b64decode(data["story_audio_b64"])
    if audio_saver is not None and input_index is not None:
        audio_saver.save_output(story_audio, index=input_index, label="output_story")
    await asyncio.to_thread(player.play_wav_bytes, story_audio)

    print("\n完成！")
