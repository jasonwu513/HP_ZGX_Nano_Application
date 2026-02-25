import logging
import os
from dataclasses import dataclass, field

import numpy as np

from edge.config import settings

logger = logging.getLogger(__name__)

_engine: "DiarizationEngine | None" = None


@dataclass
class SpeakerInfo:
    speaker_id: int
    label: str
    enrolled: bool = False      # 是否為預先註冊的聲紋
    embeddings: list = field(default_factory=list)
    centroid: np.ndarray = field(default_factory=lambda: np.zeros(256, dtype=np.float32))


class DiarizationEngine:
    def __init__(
        self,
        model_path: str,
        cosine_threshold: float = 0.38,
        max_speakers: int | None = None,
        max_embeddings_per_speaker: int = 50,
    ):
        self._cosine_threshold = cosine_threshold
        self._max_speakers = max_speakers
        self._max_embeddings = max_embeddings_per_speaker
        self._speakers: list[SpeakerInfo] = []
        self._next_guest_id = 1

        # 載入 ONNX 模型
        import onnxruntime as ort

        model_file = os.path.join(model_path, "embedding_model.onnx")
        logger.info("載入 WeSpeaker embedding 模型: %s", model_file)
        self._session = ort.InferenceSession(model_file)
        self._input_name = self._session.get_inputs()[0].name

        # 載入已註冊的聲紋 profile
        self._load_profiles(model_path)

    def _load_profiles(self, model_path: str):
        profiles_dir = os.path.join(model_path, "profiles")
        if not os.path.isdir(profiles_dir):
            logger.info("無聲紋 profile 目錄: %s", profiles_dir)
            return

        for fname in sorted(os.listdir(profiles_dir)):
            if not fname.endswith(".npy"):
                continue
            name = fname[:-4]  # 去掉 .npy
            filepath = os.path.join(profiles_dir, fname)
            centroid = np.load(filepath).astype(np.float32)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            speaker = SpeakerInfo(
                speaker_id=len(self._speakers) + 1,
                label=name,
                enrolled=True,
                embeddings=[centroid],
                centroid=centroid,
            )
            self._speakers.append(speaker)
            logger.info("載入聲紋 profile: %s", name)

        if self._speakers:
            logger.info("共載入 %d 個聲紋 profile", len(self._speakers))

    def _extract_fbank(self, pcm_float: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        import kaldi_native_fbank as knf

        opts = knf.FbankOptions()
        opts.frame_opts.samp_freq = sample_rate
        opts.frame_opts.frame_length_ms = 25.0
        opts.frame_opts.frame_shift_ms = 10.0
        opts.mel_opts.num_bins = 80

        fbank = knf.OnlineFbank(opts)
        fbank.accept_waveform(sample_rate, pcm_float.tolist())
        fbank.input_finished()

        num_frames = fbank.num_frames_ready
        if num_frames == 0:
            return np.zeros((0, 80), dtype=np.float32)

        features = np.zeros((num_frames, 80), dtype=np.float32)
        for i in range(num_frames):
            features[i] = fbank.get_frame(i)

        # CMN (cepstral mean normalization)
        features -= features.mean(axis=0, keepdims=True)

        return features

    def _extract_embedding(self, pcm_data: bytes, sample_rate: int = 16000) -> np.ndarray:
        pcm_float = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

        fbank_features = self._extract_fbank(pcm_float, sample_rate)
        if fbank_features.shape[0] == 0:
            return np.zeros(256, dtype=np.float32)

        # [T, 80] -> [1, T, 80]
        inp = fbank_features[np.newaxis, :, :].astype(np.float32)
        outputs = self._session.run(None, {self._input_name: inp})
        embedding = outputs[0].flatten().astype(np.float32)

        # L2 正規化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def extract_embedding(self, pcm_data: bytes, sample_rate: int = 16000) -> np.ndarray:
        """公開介面，供 enroll_speaker 使用。"""
        return self._extract_embedding(pcm_data, sample_rate)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))

    def _update_centroid(self, speaker: SpeakerInfo, new_embedding: np.ndarray):
        speaker.embeddings.append(new_embedding)
        if len(speaker.embeddings) > self._max_embeddings:
            speaker.embeddings = speaker.embeddings[-self._max_embeddings:]
        centroid = np.mean(speaker.embeddings, axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        speaker.centroid = centroid

    def identify(self, pcm_data: bytes, sample_rate: int = 16000) -> str:
        embedding = self._extract_embedding(pcm_data, sample_rate)

        if not self._speakers:
            return self._create_guest(embedding)

        # 計算與所有已知說話者的 cosine similarity
        best_score = -1.0
        best_speaker: SpeakerInfo | None = None
        for speaker in self._speakers:
            score = self._cosine_similarity(embedding, speaker.centroid)
            if score > best_score:
                best_score = score
                best_speaker = speaker

        if best_score >= self._cosine_threshold:
            self._update_centroid(best_speaker, embedding)
            logger.debug("說話者匹配: %s (score=%.3f)", best_speaker.label, best_score)
            return best_speaker.label

        # 若已達 max_speakers 上限，強制匹配最接近的
        if self._max_speakers is not None and len(self._speakers) >= self._max_speakers:
            self._update_centroid(best_speaker, embedding)
            logger.debug("已達說話者上限，強制匹配: %s (score=%.3f)", best_speaker.label, best_score)
            return best_speaker.label

        return self._create_guest(embedding)

    def _create_guest(self, embedding: np.ndarray) -> str:
        guest_id = self._next_guest_id
        self._next_guest_id += 1
        label = f"訪客 {guest_id}"
        speaker = SpeakerInfo(
            speaker_id=len(self._speakers) + 1,
            label=label,
            enrolled=False,
            embeddings=[embedding],
            centroid=embedding.copy(),
        )
        self._speakers.append(speaker)
        logger.info("新增訪客說話者: %s", label)
        return label


def load():
    global _engine
    _engine = DiarizationEngine(
        model_path=settings.diarize_model_path,
        cosine_threshold=settings.diarize_cosine_threshold,
        max_speakers=settings.diarize_num_speakers,
    )
    logger.info("說話者辨識模組載入完成")


def identify(pcm_data: bytes, sample_rate: int = 16000) -> str | None:
    if _engine is None:
        return None
    return _engine.identify(pcm_data, sample_rate)
