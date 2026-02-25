import asyncio
import io
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Dispatch tests
# ---------------------------------------------------------------------------
class TestDispatch:
    @pytest.mark.parametrize(
        "backend_name, class_name",
        [
            ("piper", "PiperBackend"),
            ("edge", "EdgeBackend"),
            ("cosyvoice", "CosyVoiceBackend"),
            ("none", "NoneBackend"),
        ],
    )
    def test_create_backend(self, backend_name, class_name):
        with patch("server.modules.tts.settings") as s:
            s.tts_backend = backend_name
            from server.modules.tts import _create_backend

            backend = _create_backend()
            assert type(backend).__name__ == class_name

    def test_create_backend_invalid(self):
        with patch("server.modules.tts.settings") as s:
            s.tts_backend = "invalid"
            from server.modules.tts import _create_backend

            with pytest.raises(ValueError, match="Unknown TTS backend"):
                _create_backend()

    @pytest.mark.asyncio
    async def test_synthesize_before_load(self):
        import server.modules.tts as tts_mod

        original = tts_mod._backend
        tts_mod._backend = None
        try:
            with pytest.raises(RuntimeError, match="TTS not loaded"):
                async for _ in tts_mod.synthesize("hello"):
                    pass
        finally:
            tts_mod._backend = original

    @pytest.mark.asyncio
    async def test_synthesize_full_before_load(self):
        import server.modules.tts as tts_mod

        original = tts_mod._backend
        tts_mod._backend = None
        try:
            with pytest.raises(RuntimeError, match="TTS not loaded"):
                await tts_mod.synthesize_full("hello")
        finally:
            tts_mod._backend = original


# ---------------------------------------------------------------------------
# None backend
# ---------------------------------------------------------------------------
class TestNoneBackend:
    @pytest.mark.asyncio
    async def test_load_succeeds(self):
        from server.modules.tts._none import NoneBackend

        backend = NoneBackend()
        await backend.load()  # should not raise

    @pytest.mark.asyncio
    async def test_synthesize_raises(self):
        from server.modules.tts._none import NoneBackend

        backend = NoneBackend()
        with pytest.raises(RuntimeError, match="TTS is disabled"):
            async for _ in backend.synthesize("hello"):
                pass

    @pytest.mark.asyncio
    async def test_synthesize_full_raises(self):
        from server.modules.tts._none import NoneBackend

        backend = NoneBackend()
        with pytest.raises(RuntimeError, match="TTS is disabled"):
            await backend.synthesize_full("hello")


# ---------------------------------------------------------------------------
# CosyVoice backend
# ---------------------------------------------------------------------------
class TestCosyVoiceBackend:
    @pytest.mark.asyncio
    async def test_synthesize_full(self):
        import torch
        from server.modules.tts._cosyvoice import CosyVoiceBackend

        backend = CosyVoiceBackend()
        mock_model = MagicMock()
        chunk = {"tts_speech": torch.randn(1, 22050)}
        mock_model.inference_cross_lingual.return_value = [chunk]
        backend._model = mock_model

        result = await backend.synthesize_full("Hello world")
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_streaming(self):
        import torch
        from server.modules.tts._cosyvoice import CosyVoiceBackend

        backend = CosyVoiceBackend()
        mock_model = MagicMock()
        chunk = {"tts_speech": torch.randn(1, 22050)}
        mock_model.inference_cross_lingual.return_value = [chunk]
        backend._model = mock_model

        chunks = []
        async for c in backend.synthesize("Hello world"):
            chunks.append(c)
        assert len(chunks) == 1
        assert isinstance(chunks[0], bytes)

    @pytest.mark.asyncio
    async def test_synthesize_raises_when_not_loaded(self):
        from server.modules.tts._cosyvoice import CosyVoiceBackend

        backend = CosyVoiceBackend()
        with pytest.raises(RuntimeError, match="CosyVoice 模型未載入"):
            await backend.synthesize_full("hello")


# ---------------------------------------------------------------------------
# Piper backend
# ---------------------------------------------------------------------------
class TestPiperBackend:
    @staticmethod
    def _make_audio_chunk(n_samples=2205, sample_rate=22050):
        import numpy as np

        mock_chunk = MagicMock()
        pcm = (np.sin(np.linspace(0, 100, n_samples)) * 32767).astype(np.int16)
        mock_chunk.audio_int16_bytes = pcm.tobytes()
        mock_chunk.sample_rate = sample_rate
        return mock_chunk

    @pytest.mark.asyncio
    async def test_synthesize_full(self):
        from server.modules.tts._piper import PiperBackend

        backend = PiperBackend()
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice.synthesize.return_value = [self._make_audio_chunk()]
        backend._voice = mock_voice

        result = await backend.synthesize_full("Hello")
        assert isinstance(result, bytes)
        assert len(result) > 44  # more than just WAV header
        with wave.open(io.BytesIO(result), "rb") as wf:
            assert wf.getnchannels() == 1

    @pytest.mark.asyncio
    async def test_synthesize_streaming(self):
        from server.modules.tts._piper import PiperBackend

        backend = PiperBackend()
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice.synthesize.return_value = [self._make_audio_chunk()]
        backend._voice = mock_voice

        chunks = []
        async for c in backend.synthesize("Hello"):
            chunks.append(c)
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_synthesize_raises_when_not_loaded(self):
        from server.modules.tts._piper import PiperBackend

        backend = PiperBackend()
        with pytest.raises(RuntimeError, match="Piper 語音模型未載入"):
            await backend.synthesize_full("hello")


# ---------------------------------------------------------------------------
# edge-tts backend
# ---------------------------------------------------------------------------
class TestEdgeBackend:
    @pytest.mark.asyncio
    async def test_synthesize_full(self):
        from server.modules.tts._edge import EdgeBackend

        backend = EdgeBackend()
        backend._ready = True

        # Create a minimal valid MP3-like data that pydub can handle
        # We'll mock _communicate and _mp3_to_wav instead
        fake_wav = io.BytesIO()
        with wave.open(fake_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * 2400)
        fake_wav_bytes = fake_wav.getvalue()

        with patch.object(
            backend, "_communicate", new_callable=AsyncMock, return_value=b"fake_mp3"
        ), patch.object(backend, "_mp3_to_wav", return_value=fake_wav_bytes):
            result = await backend.synthesize_full("Hello")
            assert isinstance(result, bytes)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_raises_when_not_ready(self):
        from server.modules.tts._edge import EdgeBackend

        backend = EdgeBackend()
        backend._ready = False
        with pytest.raises(RuntimeError, match="edge-tts 未載入"):
            await backend.synthesize_full("hello")
