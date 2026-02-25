import io
import logging
import wave

import sounddevice as sd
import numpy as np

logger = logging.getLogger(__name__)


class AudioPlayer:
    def play_wav_bytes(self, wav_bytes: bytes):
        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                pcm = wf.readframes(wf.getnframes())

            audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels)

            sd.play(audio, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            logger.error("播放失敗: %s", e)

    def play_chunks(self, chunks: list[bytes]):
        for chunk in chunks:
            self.play_wav_bytes(chunk)
