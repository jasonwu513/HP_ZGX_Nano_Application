"""
Qwen3-ASR 純 numpy processor（改編自 dseditor/QwenASRMiniTool processor_numpy.py）。

功能：Mel 特徵提取 + BPE 解碼 + Prompt 組裝
依賴：numpy（已有）、pathlib（標準庫）
"""
from __future__ import annotations

import json
import numpy as np
from pathlib import Path

# Mel 參數（對齊 WhisperFeatureExtractor）
_N_FFT = 400
_HOP = 160
_N_MELS = 128
_N_SAMPLES = 480_000  # 30s * 16000
_NB_FRAMES = 3000

_MEL_FILTERS: np.ndarray | None = None
_HANN_WINDOW: np.ndarray = np.hanning(_N_FFT + 1)[:-1].astype(np.float32)


def _load_mel_filters(model_dir: Path) -> np.ndarray:
    global _MEL_FILTERS
    if _MEL_FILTERS is not None:
        return _MEL_FILTERS

    for p in [model_dir / "mel_filters.npy", model_dir.parent / "mel_filters.npy"]:
        if p.exists():
            raw = np.load(str(p))
            if raw.shape == (_N_MELS, _N_FFT // 2 + 1):
                _MEL_FILTERS = raw.astype(np.float32)
            elif raw.shape == (_N_FFT // 2 + 1, _N_MELS):
                _MEL_FILTERS = raw.T.astype(np.float32)
            else:
                raise ValueError(f"mel_filters.npy shape {raw.shape} 不符預期")
            return _MEL_FILTERS

    raise FileNotFoundError(f"找不到 mel_filters.npy（搜尋路徑: {model_dir}）")


# BPE 解碼（byte-level GPT-2）

def _build_byte_decoder() -> dict[str, int]:
    bs = (list(range(ord("!"), ord("~") + 1))
          + list(range(ord("¡"), ord("¬") + 1))
          + list(range(ord("®"), ord("ÿ") + 1)))
    cs = list(bs)
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


_BYTE_DECODER: dict[str, int] = _build_byte_decoder()


def _bpe_decode(token_strings: list[str]) -> str:
    merged = "".join(token_strings)
    byte_vals = [_BYTE_DECODER[ch] for ch in merged if ch in _BYTE_DECODER]
    try:
        return bytes(byte_vals).decode("utf-8", errors="replace")
    except Exception:
        return merged


class LightProcessor:
    """Qwen3-ASR processor：mel 提取 + prompt 組裝 + BPE 解碼。"""

    def __init__(self, model_dir: Path):
        _load_mel_filters(model_dir)
        self._model_dir = model_dir

        tpl_path = model_dir / "prompt_template.json"
        with open(tpl_path, "r", encoding="utf-8") as f:
            tpl = json.load(f)

        self._prefix_ids: list[int] = tpl["prefix_ids"]
        self._suffix_ids: list[int] = tpl["suffix_ids"]
        self._n_audio: int = tpl["n_audio_tokens"]
        self.pad_id: int = tpl["audio_pad_id"]
        self.eos_id: int = tpl["eos_id"]
        self.eot_id: int = tpl["eot_id"]
        self._special_ids: set[int] = set(tpl["special_ids"])
        self._n_samples: int = tpl.get("n_samples", _N_SAMPLES)
        self._nb_frames: int = tpl.get("nb_frames", _NB_FRAMES)

        self._language_suffix_ids: dict[str, list[int]] = tpl.get("language_suffix_ids", {})

        # id → token string 對映
        vocab_path = model_dir / "vocab.json"
        with open(vocab_path, "r", encoding="utf-8") as f:
            vocab: dict[str, int] = json.load(f)
        self._id2str: dict[int, str] = {v: k for k, v in vocab.items()}

        tc_path = model_dir / "tokenizer_config.json"
        with open(tc_path, "r", encoding="utf-8") as f:
            tc = json.load(f)
        for tok_id_str, info in tc.get("added_tokens_decoder", {}).items():
            self._id2str[int(tok_id_str)] = info["content"]

    def extract_mel(self, audio: np.ndarray) -> np.ndarray:
        """16kHz float32 音訊 → [1, 128, nb_frames] mel"""
        audio = audio.astype(np.float32)
        if len(audio) > self._n_samples:
            audio = audio[:self._n_samples]
        if len(audio) < self._n_samples:
            audio = np.pad(audio, (0, self._n_samples - len(audio)))

        half = _N_FFT // 2
        audio_c = np.pad(audio, half, mode="reflect")
        frames = np.lib.stride_tricks.sliding_window_view(audio_c, _N_FFT)[::_HOP]
        frames = frames[:self._nb_frames].astype(np.float32)
        windowed = frames * _HANN_WINDOW

        stft = np.fft.rfft(windowed, axis=1)
        power = np.abs(stft).astype(np.float32) ** 2
        mel = (_load_mel_filters(self._model_dir) @ power.T)

        log_mel = np.log10(np.maximum(mel, 1e-10))
        log_mel = np.maximum(log_mel, log_mel.max() - 8.0)
        log_mel = (log_mel + 4.0) / 4.0
        return log_mel[np.newaxis, :, :].astype(np.float32)

    def prepare(self, audio: np.ndarray, language: str | None = None) -> tuple[np.ndarray, np.ndarray]:
        """回傳 (mel, input_ids)"""
        mel = self.extract_mel(audio)

        suffix_ids = self._suffix_ids
        if language and language in self._language_suffix_ids:
            suffix_ids = self._suffix_ids + self._language_suffix_ids[language]

        ids = np.array(
            self._prefix_ids + [self.pad_id] * self._n_audio + suffix_ids,
            dtype=np.int64,
        )[np.newaxis, :]
        return mel, ids

    def decode(self, token_ids: list[int], skip_special: bool = True) -> str:
        parts: list[str] = []
        for tid in token_ids:
            if skip_special and tid in self._special_ids:
                continue
            s = self._id2str.get(tid, "")
            if s:
                parts.append(s)
        return _bpe_decode(parts)
