import os
import tempfile

import numpy as np
import pytest

from edge.modules.diarization import DiarizationEngine, SpeakerInfo


class FakeEngine(DiarizationEngine):
    """跳過 ONNX 模型載入，直接使用 mock embedding。"""

    def __init__(self, cosine_threshold=0.38, max_speakers=None, profiles_dir=None):
        self._cosine_threshold = cosine_threshold
        self._max_speakers = max_speakers
        self._max_embeddings = 50
        self._speakers: list[SpeakerInfo] = []
        self._next_guest_id = 1
        self._mock_embedding: np.ndarray | None = None

        # 載入 profiles（如果提供）
        if profiles_dir and os.path.isdir(profiles_dir):
            self._load_profiles_from_dir(profiles_dir)

    def _load_profiles_from_dir(self, profiles_dir: str):
        """從目錄載入 profile，不需要 ONNX session。"""
        for fname in sorted(os.listdir(profiles_dir)):
            if not fname.endswith(".npy"):
                continue
            name = fname[:-4]
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

    def _extract_embedding(self, pcm_data: bytes, sample_rate: int = 16000) -> np.ndarray:
        """使用預設的 mock embedding 而非實際的 ONNX 推理。"""
        if self._mock_embedding is not None:
            return self._mock_embedding.copy()
        # 根據 pcm_data 產生一個確定性的 embedding
        rng = np.random.RandomState(hash(pcm_data) % (2**31))
        emb = rng.randn(256).astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb /= norm
        return emb

    def set_mock_embedding(self, emb: np.ndarray):
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        self._mock_embedding = emb


def _make_pcm(seed: int, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """產生具有確定性的假 PCM 資料。"""
    rng = np.random.RandomState(seed)
    n_samples = int(duration * sample_rate)
    samples = (rng.randn(n_samples) * 1000).astype(np.int16)
    return samples.tobytes()


class TestGuestSpeakerCreation:
    def test_first_segment_creates_guest_1(self):
        engine = FakeEngine()
        label = engine.identify(_make_pcm(42))
        assert label == "訪客 1"

    def test_different_segments_create_different_guests(self):
        engine = FakeEngine(cosine_threshold=0.99)
        label1 = engine.identify(_make_pcm(1))
        label2 = engine.identify(_make_pcm(2))
        assert label1 == "訪客 1"
        assert label2 == "訪客 2"


class TestSameSpeakerMatching:
    def test_same_embedding_matches(self):
        engine = FakeEngine(cosine_threshold=0.38)
        emb = np.random.randn(256).astype(np.float32)
        engine.set_mock_embedding(emb)

        label1 = engine.identify(_make_pcm(1))
        label2 = engine.identify(_make_pcm(2))
        assert label1 == "訪客 1"
        assert label2 == "訪客 1"

    def test_centroid_updates_on_match(self):
        engine = FakeEngine(cosine_threshold=0.38)
        emb = np.random.randn(256).astype(np.float32)
        engine.set_mock_embedding(emb)

        engine.identify(_make_pcm(1))

        emb2 = emb + np.random.randn(256).astype(np.float32) * 0.01
        engine.set_mock_embedding(emb2)
        engine.identify(_make_pcm(2))

        assert len(engine._speakers[0].embeddings) == 2


class TestMaxSpeakersLimit:
    def test_max_speakers_forces_match(self):
        engine = FakeEngine(cosine_threshold=0.99, max_speakers=2)

        emb1 = np.zeros(256, dtype=np.float32)
        emb1[0] = 1.0
        engine.set_mock_embedding(emb1)
        label1 = engine.identify(_make_pcm(1))

        emb2 = np.zeros(256, dtype=np.float32)
        emb2[1] = 1.0
        engine.set_mock_embedding(emb2)
        label2 = engine.identify(_make_pcm(2))

        assert label1 == "訪客 1"
        assert label2 == "訪客 2"

        emb3 = np.zeros(256, dtype=np.float32)
        emb3[2] = 1.0
        engine.set_mock_embedding(emb3)
        label3 = engine.identify(_make_pcm(3))

        assert label3 in ("訪客 1", "訪客 2")
        assert len(engine._speakers) == 2


class TestCosineThresholdBoundary:
    def test_exactly_at_threshold_matches(self):
        engine = FakeEngine(cosine_threshold=0.5)

        emb1 = np.zeros(256, dtype=np.float32)
        emb1[0] = 1.0
        engine.set_mock_embedding(emb1)
        engine.identify(_make_pcm(1))

        emb2 = np.zeros(256, dtype=np.float32)
        emb2[0] = 1.0
        emb2[1] = 1.0  # cosine with emb1 = 1/sqrt(2) ≈ 0.707 > 0.5
        engine.set_mock_embedding(emb2)
        label = engine.identify(_make_pcm(2))
        assert label == "訪客 1"

    def test_below_threshold_creates_new(self):
        engine = FakeEngine(cosine_threshold=0.99)

        emb1 = np.zeros(256, dtype=np.float32)
        emb1[0] = 1.0
        engine.set_mock_embedding(emb1)
        engine.identify(_make_pcm(1))

        emb2 = np.zeros(256, dtype=np.float32)
        emb2[1] = 1.0
        engine.set_mock_embedding(emb2)
        label = engine.identify(_make_pcm(2))
        assert label == "訪客 2"


class TestProfileEnrollment:
    def test_enrolled_profile_matched_by_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # 建立 profile
            emb = np.zeros(256, dtype=np.float32)
            emb[0] = 1.0
            np.save(os.path.join(tmpdir, "阿公.npy"), emb)

            engine = FakeEngine(cosine_threshold=0.5, profiles_dir=tmpdir)

            # 用相同 embedding 辨識，應匹配 profile
            engine.set_mock_embedding(emb)
            label = engine.identify(_make_pcm(1))
            assert label == "阿公"

    def test_unknown_speaker_becomes_guest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emb = np.zeros(256, dtype=np.float32)
            emb[0] = 1.0
            np.save(os.path.join(tmpdir, "媽媽.npy"), emb)

            engine = FakeEngine(cosine_threshold=0.99, profiles_dir=tmpdir)

            # 用完全不同的 embedding，不應匹配 profile
            emb2 = np.zeros(256, dtype=np.float32)
            emb2[1] = 1.0
            engine.set_mock_embedding(emb2)
            label = engine.identify(_make_pcm(1))
            assert label == "訪客 1"

    def test_multiple_profiles_correct_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emb_grandpa = np.zeros(256, dtype=np.float32)
            emb_grandpa[0] = 1.0
            np.save(os.path.join(tmpdir, "阿公.npy"), emb_grandpa)

            emb_mom = np.zeros(256, dtype=np.float32)
            emb_mom[1] = 1.0
            np.save(os.path.join(tmpdir, "媽媽.npy"), emb_mom)

            engine = FakeEngine(cosine_threshold=0.5, profiles_dir=tmpdir)

            # 匹配阿公
            engine.set_mock_embedding(emb_grandpa)
            assert engine.identify(_make_pcm(1)) == "阿公"

            # 匹配媽媽
            engine.set_mock_embedding(emb_mom)
            assert engine.identify(_make_pcm(2)) == "媽媽"

    def test_enrolled_speakers_not_counted_as_guests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emb = np.zeros(256, dtype=np.float32)
            emb[0] = 1.0
            np.save(os.path.join(tmpdir, "姊姊.npy"), emb)

            engine = FakeEngine(cosine_threshold=0.99, profiles_dir=tmpdir)

            # 不匹配 profile 的 embedding → 訪客，編號從 1 開始
            emb2 = np.zeros(256, dtype=np.float32)
            emb2[5] = 1.0
            engine.set_mock_embedding(emb2)
            label = engine.identify(_make_pcm(1))
            assert label == "訪客 1"
