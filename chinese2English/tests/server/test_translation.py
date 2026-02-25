from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_model():
    # Mock tokenizer
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = "formatted prompt"

    # tokenizer(text, return_tensors="pt") returns an object with .to()
    input_ids = MagicMock()
    input_ids.shape = [1, 10]
    tokenizer_output = MagicMock()
    tokenizer_output.__getitem__ = lambda self, key: input_ids if key == "input_ids" else MagicMock()
    tokenizer_output.to.return_value = tokenizer_output
    mock_tokenizer.return_value = tokenizer_output

    mock_tokenizer.decode.return_value = "Hello world"

    # Mock model
    mock_m = MagicMock()
    mock_m.device = "cpu"
    generated_token = MagicMock()
    generated_sequence = MagicMock()
    generated_sequence.__getitem__ = lambda self, key: generated_token
    mock_m.generate.return_value = MagicMock(__getitem__=lambda self, idx: generated_sequence)

    with patch("server.modules.translation._model", mock_m), \
         patch("server.modules.translation._tokenizer", mock_tokenizer):
        yield mock_m, mock_tokenizer


@pytest.mark.asyncio
async def test_translate_sentence(mock_model):
    from server.modules.translation import translate_sentence

    result = await translate_sentence("你好世界")
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_translate_batch(mock_model):
    from server.modules.translation import translate_batch

    result = await translate_batch(["你好", "世界"])
    assert result.direct_translation == "Hello world"
    assert result.child_story == "Hello world"
