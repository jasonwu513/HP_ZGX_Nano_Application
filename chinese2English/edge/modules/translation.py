import logging
import re
import time

from llama_cpp import Llama

from edge.config import settings

logger = logging.getLogger(__name__)

_llm: Llama | None = None

SYSTEM_PROMPT = (
    "You are a Taiwanese Mandarin to English translator for a children's language learning tool. "
    "The input is spoken Taiwanese Mandarin (may contain simplified chars from ASR). "
    "Translate into natural, simple English. "
    "Output ONLY the English translation, nothing else. /no_think"
)


def load():
    global _llm
    logger.info("載入翻譯模型: %s ...", settings.translation_model_path)
    _llm = Llama(
        model_path=settings.translation_model_path,
        n_gpu_layers=0,
        n_threads=settings.translation_num_threads,
        n_ctx=settings.translation_ctx_size,
        verbose=False,
    )
    logger.info("翻譯模型載入完成")


def _strip_think_blocks(text: str) -> str:
    # Strip closed <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip unclosed <think> block (truncated by max_tokens)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    # Remove any remaining special tokens
    text = re.sub(r"<\|[^>]+\|>", "", text)
    return text.strip()


def translate(chinese: str) -> str:
    if _llm is None:
        raise RuntimeError("翻譯模型未載入，請先呼叫 load()")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": chinese},
    ]

    t0 = time.perf_counter()
    response = _llm.create_chat_completion(
        messages=messages,
        max_tokens=256,
        temperature=0.0,
    )
    elapsed = time.perf_counter() - t0

    raw = response["choices"][0]["message"]["content"] or ""
    result = _strip_think_blocks(raw)

    usage = response.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    tokens_per_sec = completion_tokens / elapsed if elapsed > 0 else 0
    logger.info(
        "翻譯: input %d tokens, output %d tokens, %.1f tok/s (%.2fs), 結果: %s",
        prompt_tokens, completion_tokens, tokens_per_sec, elapsed, result,
    )
    return result
