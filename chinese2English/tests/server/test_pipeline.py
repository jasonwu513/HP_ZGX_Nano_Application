from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_process_realtime():
    with patch("server.modules.asr.transcribe", new_callable=AsyncMock) as mock_asr, \
         patch("server.modules.translation.translate_sentence", new_callable=AsyncMock) as mock_trans, \
         patch("server.modules.tts.synthesize") as mock_tts:

        mock_asr.return_value = "你好"
        mock_trans.return_value = "Hello"

        async def fake_synthesize(text):
            yield b"audio_chunk"

        mock_tts.side_effect = fake_synthesize

        from server.pipeline import PipelineManager
        pm = PipelineManager()
        await pm.start()

        transcript, english, chunks = await pm.process_realtime(b"fake_audio")

        assert transcript == "你好"
        assert english == "Hello"
        assert len(chunks) == 1

        await pm.stop()
