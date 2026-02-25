import logging
import time
from pathlib import Path

import numpy as np

from shared.audio_utils import decode_wav
from edge.config import settings

logger = logging.getLogger(__name__)

# sherpa-onnx backends 使用 _recognizer
_recognizer = None

# qwen3 backend 使用 _qwen3_engine
_qwen3_engine = None

_active_backend: str = ""


# ── Sherpa-ONNX loaders ──────────────────────────────────────────────

def _load_sensevoice(model_path: str, num_threads: int):
    import sherpa_onnx
    logger.info("載入 Sherpa-ONNX SenseVoice 模型: %s ...", model_path)
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=f"{model_path}/model.onnx",
        tokens=f"{model_path}/tokens.txt",
        num_threads=num_threads,
    )


def _load_breeze(model_path: str, num_threads: int):
    import sherpa_onnx
    logger.info("載入 Sherpa-ONNX Breeze-ASR (Whisper) 模型: %s ...", model_path)
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{model_path}/breeze-asr-25-encoder.onnx",
        decoder=f"{model_path}/breeze-asr-25-decoder.onnx",
        tokens=f"{model_path}/breeze-asr-25-tokens.txt",
        language="zh",
        num_threads=num_threads,
    )


def _load_breeze_int8(model_path: str, num_threads: int):
    import sherpa_onnx
    logger.info("載入 Sherpa-ONNX Breeze-ASR INT8 (Whisper) 模型: %s ...", model_path)
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{model_path}/breeze-asr-25-half-encoder.int8.onnx",
        decoder=f"{model_path}/breeze-asr-25-half-decoder.int8.onnx",
        tokens=f"{model_path}/breeze-asr-25-half-tokens.txt",
        language="zh",
        num_threads=num_threads,
    )


_SHERPA_BACKENDS = {
    "sensevoice": _load_sensevoice,
    "breeze": _load_breeze,
    "breeze-int8": _load_breeze_int8,
}


# ── Qwen3 OpenVINO engine ───────────────────────────────────────────

class _Qwen3Engine:
    """Qwen3-ASR OpenVINO INT8 推理引擎（改編自 dseditor/QwenASRMiniTool）。"""

    def __init__(self, model_path: str):
        import openvino as ov
        from edge.modules.qwen3_processor import LightProcessor

        model_dir = Path(model_path)
        logger.info("載入 Qwen3-ASR OpenVINO INT8 模型: %s ...", model_dir)

        core = ov.Core()
        self.audio_enc = core.compile_model(str(model_dir / "audio_encoder_model.xml"), "CPU")
        self.embedder = core.compile_model(str(model_dir / "thinker_embeddings_model.xml"), "CPU")
        dec_comp = core.compile_model(str(model_dir / "decoder_model.xml"), "CPU")
        self.dec_req = dec_comp.create_infer_request()

        self.processor = LightProcessor(model_dir)
        self.pad_id = self.processor.pad_id

    def transcribe(self, samples: np.ndarray, max_tokens: int = 300) -> str:
        mel, ids = self.processor.prepare(samples, language="Chinese")

        # 音訊編碼 + token embedding
        ae = list(self.audio_enc({"mel": mel}).values())[0]
        te = list(self.embedder({"input_ids": ids}).values())[0]

        # 音訊特徵填入 pad 位置
        combined = te.copy()
        mask = ids[0] == self.pad_id
        np_ = int(mask.sum())
        na = ae.shape[1]
        if np_ != na:
            mn = min(np_, na)
            combined[0, np.where(mask)[0][:mn]] = ae[0, :mn]
        else:
            combined[0, mask] = ae[0]

        # 自回歸解碼
        seq_len = combined.shape[1]
        pos = np.arange(seq_len, dtype=np.int64)[np.newaxis, :]
        self.dec_req.reset_state()
        out = self.dec_req.infer({0: combined, "position_ids": pos})
        logits = list(out.values())[0]

        eos = self.processor.eos_id
        eot = self.processor.eot_id
        gen: list[int] = []
        nxt = int(np.argmax(logits[0, -1, :]))
        cur = seq_len
        while nxt not in (eos, eot) and len(gen) < max_tokens:
            gen.append(nxt)
            emb = list(self.embedder(
                {"input_ids": np.array([[nxt]], dtype=np.int64)}
            ).values())[0]
            out = self.dec_req.infer(
                {0: emb, "position_ids": np.array([[cur]], dtype=np.int64)}
            )
            logits = list(out.values())[0]
            nxt = int(np.argmax(logits[0, -1, :]))
            cur += 1

        raw = self.processor.decode(gen)
        if "<asr_text>" in raw:
            raw = raw.split("<asr_text>", 1)[1]
        return raw.strip()


# ── Public API ───────────────────────────────────────────────────────

_ALL_BACKENDS = list(_SHERPA_BACKENDS) + ["qwen3"]


def load():
    global _recognizer, _qwen3_engine, _active_backend
    backend = settings.asr_backend.lower()

    if backend == "qwen3":
        _qwen3_engine = _Qwen3Engine(settings.asr_model_path)
    elif backend in _SHERPA_BACKENDS:
        _recognizer = _SHERPA_BACKENDS[backend](settings.asr_model_path, settings.asr_num_threads)
    else:
        raise ValueError(f"不支援的 ASR backend: {backend!r}，可用: {', '.join(_ALL_BACKENDS)}")

    _active_backend = backend
    logger.info("ASR 模型載入完成 (backend=%s)", backend)


def transcribe(wav_bytes: bytes) -> str:
    pcm_data, sample_rate = decode_wav(wav_bytes)
    samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
    duration = len(samples) / sample_rate

    t0 = time.perf_counter()

    if _active_backend == "qwen3":
        if _qwen3_engine is None:
            raise RuntimeError("ASR 模型未載入，請先呼叫 load()")
        text = _qwen3_engine.transcribe(samples)
    else:
        if _recognizer is None:
            raise RuntimeError("ASR 模型未載入，請先呼叫 load()")
        stream = _recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        _recognizer.decode_stream(stream)
        text = stream.result.text.strip()

    elapsed = time.perf_counter() - t0
    rtf = elapsed / duration if duration > 0 else 0
    logger.info("ASR: %.2fs 音訊, %.2fs 處理, RTF=%.2f, 結果: %s", duration, elapsed, rtf, text)
    return text
