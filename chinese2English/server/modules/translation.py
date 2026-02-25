import asyncio
import logging
import re
import time
from functools import partial

import torch
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from server.config import settings

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_gpu_lock = asyncio.Lock()


class BatchTranslation(BaseModel):
    direct_translation: str
    child_story: str


def _load_model():
    global _model, _tokenizer
    logger.info("載入翻譯模型: %s ...", settings.translation_model_id)

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    _tokenizer = AutoTokenizer.from_pretrained(settings.translation_model_id)

    load_kwargs = dict(
        dtype=dtype,
        device_map="auto",
    )
    if torch.cuda.is_available():
        free_bytes = torch.cuda.mem_get_info()[0]
        load_kwargs["max_memory"] = {
            0: int(free_bytes * 0.50),
            "cpu": "16GiB",
        }
        logger.info("GPU 剩餘 VRAM: %.1f MiB，超出部分將 offload 到 CPU",
                     free_bytes / 1024 / 1024)

    _model = AutoModelForCausalLM.from_pretrained(
        settings.translation_model_id,
        **load_kwargs,
    )
    logger.info("翻譯模型載入完成")


def _generate_sync(prompt: str) -> str:
    messages = [
        {"role": "user", "content": prompt},
    ]
    text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    device = next(_model.parameters()).device
    inputs = _tokenizer(text, return_tensors="pt").to(device)
    input_token_count = inputs["input_ids"].shape[1]

    t0 = time.perf_counter()
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
        )
    elapsed = time.perf_counter() - t0

    # Decode only the newly generated tokens
    generated_ids = outputs[0][input_token_count:]
    output_token_count = len(generated_ids)
    tokens_per_sec = output_token_count / elapsed if elapsed > 0 else 0
    logger.info(
        "翻譯生成: input %d tokens, output %d tokens, %.1f tok/s (%.2fs)",
        input_token_count, output_token_count, tokens_per_sec, elapsed,
    )

    raw = _tokenizer.decode(generated_ids, skip_special_tokens=False)
    # Strip <think>...</think> block that Qwen3 may emit despite enable_thinking=False
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    # Remove any remaining special tokens
    raw = re.sub(r"<\|[^>]+\|>", "", raw)
    return raw.strip()


async def load():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _load_model)


async def _call_model(prompt: str) -> str:
    if _model is None:
        raise RuntimeError("翻譯模型未載入，請先呼叫 load()")

    loop = asyncio.get_running_loop()
    async with _gpu_lock:
        return await loop.run_in_executor(None, partial(_generate_sync, prompt))


async def translate_sentence(chinese: str) -> str:
    prompt = (
        "You are a Chinese-to-English translator for a children's language learning tool.\n"
        "Translate the following Chinese sentence into natural, simple English.\n"
        "Output ONLY the English translation, nothing else.\n\n"
        f"Chinese: {chinese}"
    )
    return (await _call_model(prompt)).strip()


async def translate_batch(segments: list[str]) -> BatchTranslation:
    combined = "\n".join(f"[{i+1}] {seg}" for i, seg in enumerate(segments))

    direct_prompt = (
        "You are a Chinese-to-English translator.\n"
        "Translate the following Chinese conversation segments into natural English.\n"
        "Keep the numbered format and preserve the conversation structure.\n"
        "Output ONLY the English translation.\n\n"
        f"{combined}"
    )

    story_prompt = (
        "You are a storyteller for children aged 3-8.\n"
        "Based on the following Chinese conversation, rewrite it as a fun, simple English story.\n"
        "Use simple vocabulary suitable for young children.\n"
        "Output ONLY the English story.\n\n"
        f"Conversation:\n{combined}"
    )

    # Sequential calls to avoid concurrent GPU access
    direct_result = await _call_model(direct_prompt)
    story_result = await _call_model(story_prompt)

    return BatchTranslation(
        direct_translation=direct_result.strip(),
        child_story=story_result.strip(),
    )
