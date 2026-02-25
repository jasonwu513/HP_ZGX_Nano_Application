from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def mock_model():
    mock_result = MagicMock()
    mock_result.text = "你好世界"

    mock_m = MagicMock()
    mock_m.transcribe.return_value = [mock_result]

    with patch("server.modules.asr._model", mock_m):
        yield mock_m


def test_transcribe_sync_returns_string(mock_model):
    from server.modules.asr import _transcribe_sync

    with patch("server.modules.asr.librosa") as mock_librosa:
        mock_librosa.load.return_value = (np.zeros(16000, dtype=np.float32), 16000)

        result = _transcribe_sync(b"fake_wav_data")
        assert isinstance(result, str)
        assert result == "你好世界"
        mock_model.transcribe.assert_called_once()
