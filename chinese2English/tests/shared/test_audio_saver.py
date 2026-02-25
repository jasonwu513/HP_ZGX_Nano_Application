import os

import pytest

from shared.audio_utils import encode_wav
from shared.audio_saver import AudioSaver


def _make_wav(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    """產生一段靜音 WAV 資料供測試用。"""
    n_samples = int(sample_rate * duration_s)
    pcm = b"\x00\x00" * n_samples
    return encode_wav(pcm, sample_rate)


class TestAudioSaver:
    def test_start_session_creates_directory(self, tmp_path):
        out_dir = str(tmp_path / "sub" / "audio")
        saver = AudioSaver(output_dir=out_dir, fmt="wav")
        saver.start_session()
        assert os.path.isdir(out_dir)

    def test_save_without_session_returns_empty(self, tmp_path):
        saver = AudioSaver(output_dir=str(tmp_path), fmt="wav")
        result = saver.save_input(_make_wav())
        assert result == ""

    def test_save_pair_wav(self, tmp_path):
        saver = AudioSaver(output_dir=str(tmp_path), fmt="wav")
        saver.start_session()
        p_in, p_out = saver.save_pair(_make_wav(), _make_wav())
        assert p_in.endswith(".wav")
        assert p_out.endswith(".wav")
        assert os.path.isfile(p_in)
        assert os.path.isfile(p_out)
        assert "_input." in p_in
        assert "_output." in p_out

    def test_save_pair_ogg(self, tmp_path):
        saver = AudioSaver(output_dir=str(tmp_path), fmt="ogg")
        saver.start_session()
        p_in, p_out = saver.save_pair(_make_wav(), _make_wav())
        assert p_in.endswith(".ogg")
        assert p_out.endswith(".ogg")
        assert os.path.isfile(p_in)
        assert os.path.isfile(p_out)

    def test_index_increments(self, tmp_path):
        saver = AudioSaver(output_dir=str(tmp_path), fmt="wav")
        saver.start_session()
        saver.save_input(_make_wav())
        assert saver.current_index == 1
        saver.save_input(_make_wav())
        assert saver.current_index == 2
        # 確認檔名包含正確的 index
        files = sorted(os.listdir(tmp_path))
        assert "_0001_" in files[0]
        assert "_0002_" in files[1]

    def test_save_output_label(self, tmp_path):
        saver = AudioSaver(output_dir=str(tmp_path), fmt="wav")
        saver.start_session()
        saver.save_input(_make_wav())
        idx = saver.current_index
        p1 = saver.save_output(_make_wav(), index=idx, label="output_direct")
        p2 = saver.save_output(_make_wav(), index=idx, label="output_story")
        assert "output_direct" in p1
        assert "output_story" in p2

    def test_ogg_smaller_than_wav(self, tmp_path):
        wav_data = _make_wav(duration_s=2.0)

        saver_wav = AudioSaver(output_dir=str(tmp_path / "wav"), fmt="wav")
        saver_wav.start_session()
        p_wav, _ = saver_wav.save_pair(wav_data, wav_data)

        saver_ogg = AudioSaver(output_dir=str(tmp_path / "ogg"), fmt="ogg")
        saver_ogg.start_session()
        p_ogg, _ = saver_ogg.save_pair(wav_data, wav_data)

        wav_size = os.path.getsize(p_wav)
        ogg_size = os.path.getsize(p_ogg)
        assert ogg_size < wav_size, f"OGG ({ogg_size}) should be smaller than WAV ({wav_size})"
