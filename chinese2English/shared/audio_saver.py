import logging
import os
from datetime import datetime

import numpy as np
import soundfile as sf

from shared.audio_utils import decode_wav

logger = logging.getLogger(__name__)


class AudioSaver:
    def __init__(self, output_dir: str = "output/audio", fmt: str = "ogg"):
        self._output_dir = output_dir
        self._fmt = fmt if fmt in ("ogg", "wav") else "ogg"
        self._session_prefix: str | None = None
        self._index = 0

    def start_session(self):
        os.makedirs(self._output_dir, exist_ok=True)
        self._session_prefix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        self._index = 0
        logger.info("AudioSaver session 開始: %s (格式: %s)", self._session_prefix, self._fmt)

    def save_input(self, wav_bytes: bytes) -> str:
        if self._session_prefix is None:
            return ""
        self._index += 1
        return self._save(wav_bytes, self._index, "input")

    def save_output(self, wav_bytes: bytes, index: int | None = None, label: str = "output") -> str:
        if self._session_prefix is None:
            return ""
        idx = index if index is not None else self._index
        return self._save(wav_bytes, idx, label)

    def save_pair(self, input_wav: bytes, output_wav: bytes) -> tuple[str, str]:
        if self._session_prefix is None:
            return "", ""
        self._index += 1
        p_in = self._save(input_wav, self._index, "input")
        p_out = self._save(output_wav, self._index, "output")
        return p_in, p_out

    @property
    def current_index(self) -> int:
        return self._index

    def _save(self, wav_bytes: bytes, index: int, label: str) -> str:
        filename = f"{self._session_prefix}_{index:04d}_{label}.{self._fmt}"
        path = os.path.join(self._output_dir, filename)
        try:
            self._write_audio(path, wav_bytes)
            logger.debug("已儲存音訊: %s", path)
            return path
        except OSError as e:
            logger.error("儲存音訊失敗: %s", e)
            return ""

    def _write_audio(self, path: str, wav_bytes: bytes):
        if self._fmt == "wav":
            with open(path, "wb") as f:
                f.write(wav_bytes)
        else:
            pcm_data, sample_rate = decode_wav(wav_bytes)
            samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            del pcm_data
            sf.write(path, samples, sample_rate, format="OGG", subtype="VORBIS")
            del samples
