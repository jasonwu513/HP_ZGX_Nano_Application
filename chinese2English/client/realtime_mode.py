import asyncio
import logging
import struct
import time

import websockets

from client.audio_capture import AudioCapture
from client.audio_player import AudioPlayer
from client.config import client_settings
from client.vad_processor import VADProcessor, VADState
from shared.audio_utils import encode_wav, decode_wav
from shared.audio_saver import AudioSaver

logger = logging.getLogger(__name__)


async def run_realtime():
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

    ws_url = f"{client_settings.server_url}/ws"
    logger.info("連線到 %s ...", ws_url)

    reconnect_delay = 1.0

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info("WebSocket 已連線")
                reconnect_delay = 1.0

                while True:
                    frame = await asyncio.to_thread(capture.read_frame, 0.5)
                    if frame is None:
                        logger.debug("read_frame 超時，queue size=%d", capture._queue.qsize())
                        continue

                    state = vad.process_frame(frame)

                    if state == VADState.SEGMENT_READY:
                        segment_pcm = vad.get_segment()

                        # --- 過濾太短 ---
                        duration = len(segment_pcm) / (client_settings.sample_rate * 2)
                        if duration < client_settings.min_segment_duration:
                            logger.debug("片段太短 (%.2fs)，丟棄", duration)
                            continue

                        # --- 過濾太小聲 ---
                        if client_settings.min_segment_energy > 0:
                            n_samples = len(segment_pcm) // 2
                            samples = struct.unpack(f"<{n_samples}h", segment_pcm)
                            energy = sum(abs(s) for s in samples) / n_samples
                            if energy < client_settings.min_segment_energy:
                                logger.debug("片段太小聲 (energy=%.0f)，丟棄", energy)
                                continue

                        wav_data = encode_wav(segment_pcm)
                        saved_index = None
                        if audio_saver is not None:
                            audio_saver.save_input(wav_data)
                            saved_index = audio_saver.current_index
                        logger.info("送出語音片段: %d bytes (%.1fs)", len(wav_data), duration)

                        t_send = time.perf_counter()
                        await ws.send(wav_data)

                        audio_chunks = []
                        logger.debug("等待伺服器回應...")
                        while True:
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=90)
                            except asyncio.TimeoutError:
                                logger.error("伺服器回應逾時 (90s)，放棄此請求")
                                break
                            if isinstance(msg, bytes):
                                audio_chunks.append(msg)
                                logger.debug("收到 audio chunk: %d bytes", len(msg))
                            elif isinstance(msg, str):
                                t_recv = time.perf_counter()
                                if msg.startswith("EOU|"):
                                    parts = msg.split("|", 2)
                                    chinese = parts[1] if len(parts) > 1 else ""
                                    english = parts[2] if len(parts) > 2 else ""
                                    logger.info("中文: %s", chinese)
                                    logger.info("英文: %s", english)
                                    logger.info("伺服器回應耗時: %.2fs, 收到 %d audio chunks",
                                                t_recv - t_send, len(audio_chunks))
                                elif msg.startswith("ERROR|"):
                                    logger.error("伺服器錯誤: %s", msg[6:])
                                break

                        if audio_chunks:
                            if audio_saver is not None and saved_index is not None:
                                all_pcm = b"".join(decode_wav(c)[0] for c in audio_chunks)
                                audio_saver.save_output(encode_wav(all_pcm), index=saved_index)
                                del all_pcm
                            t_play = time.perf_counter()
                            await asyncio.to_thread(player.play_chunks, audio_chunks)
                            logger.info("播放完成 (%.2fs)", time.perf_counter() - t_play)
                            # 播放完畢：清空錄音緩衝 + 重置 VAD，避免迴音觸發
                            capture.drain()
                            vad.reset()

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning("連線失敗: %s，%0.1f 秒後重連...", e, reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 30.0)

        except KeyboardInterrupt:
            break

    capture.stop()
    logger.info("即時模式已結束")
