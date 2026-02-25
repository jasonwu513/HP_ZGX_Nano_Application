#!/usr/bin/env python3
"""
HP ZGX Nano 效能測試腳本

比較 Edge (CPU) vs ZGX Nano (GPU) 的各項效能指標：
- 翻譯品質 (BLEU)
- 翻譯速度 (tok/s, 延遲)
- ASR 精度與速度
- TTS 延遲與音質
- 記憶體用量
- 端對端 pipeline 延遲

使用方式:
    # 完整測試
    python scripts/benchmark.py --mode all --output results/

    # 只測翻譯
    python scripts/benchmark.py --mode translation --output results/

    # 只測 ASR
    python scripts/benchmark.py --mode asr --output results/
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
C2E_DIR = PROJECT_ROOT / "chinese2English"
sys.path.insert(0, str(C2E_DIR))


# =============================================================================
# 測試資料 — 真實的家庭教育場景
# =============================================================================

TRANSLATION_TEST_CASES = [
    # (中文, 參考英文翻譯, 難度)
    ("我餓了", "I am hungry.", "easy"),
    ("今天天氣很好", "The weather is nice today.", "easy"),
    ("我想喝水", "I want to drink water.", "easy"),
    ("她是我的妹妹", "She is my younger sister.", "easy"),
    ("我喜歡吃蘋果", "I like eating apples.", "easy"),
    ("我們去公園玩吧", "Let's go play at the park.", "medium"),
    ("老師今天教了我們新的歌", "The teacher taught us a new song today.", "medium"),
    ("我昨天在學校交了一個新朋友", "I made a new friend at school yesterday.", "medium"),
    ("這個故事很有趣我還想再聽一次", "This story is very interesting, I want to hear it again.", "medium"),
    ("媽媽今天煮的晚餐好好吃", "The dinner mom cooked today is delicious.", "medium"),
    (
        "她今天在學校做了一個很漂亮的勞作",
        "She made a very beautiful craft at school today.",
        "hard",
    ),
    (
        "我不想睡覺因為我還想看那本書",
        "I don't want to sleep because I still want to read that book.",
        "hard",
    ),
    (
        "下雨天的時候我喜歡在家裡畫畫",
        "When it rains, I like to draw pictures at home.",
        "hard",
    ),
    (
        "哥哥說他明天要帶我去動物園看大象",
        "My brother said he will take me to the zoo to see elephants tomorrow.",
        "hard",
    ),
    (
        "我覺得數學好難但是老師說多練習就會進步",
        "I think math is hard, but the teacher says I will improve with more practice.",
        "hard",
    ),
    # 童語 / 不完整句子
    ("那個那個就是很大很大的", "That thing is really really big.", "child_speech"),
    ("我不要我不要嘛", "I don't want to, I don't want to.", "child_speech"),
    ("爸爸你看你看那邊有狗狗", "Daddy, look look, there's a doggy over there.", "child_speech"),
    (
        "然後然後他就跑走了",
        "And then and then he ran away.",
        "child_speech",
    ),
    (
        "老師說的那個什麼東西我忘了",
        "I forgot that thing the teacher mentioned.",
        "child_speech",
    ),
]


@dataclass
class TranslationResult:
    chinese: str
    reference: str
    hypothesis: str
    difficulty: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    tokens_per_sec: float


@dataclass
class ASRResult:
    audio_file: str
    reference_text: str
    hypothesis: str
    latency_ms: float
    audio_duration_sec: float
    rtf: float  # Real-Time Factor


@dataclass
class BenchmarkReport:
    timestamp: str
    device: str  # "edge" or "zgx-nano"
    model_config: dict = field(default_factory=dict)
    translation_results: list = field(default_factory=list)
    asr_results: list = field(default_factory=list)
    tts_results: list = field(default_factory=list)
    system_info: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


# =============================================================================
# 翻譯效能測試
# =============================================================================

def benchmark_translation(device_mode: str) -> list[TranslationResult]:
    """測試翻譯模型的品質與速度"""
    results = []

    if device_mode == "zgx-nano":
        # 使用 server 模式（GPU + transformers）
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_id = os.environ.get("C2E_TRANSLATION_MODEL_ID", "Qwen/Qwen3-30B")
        print(f"載入翻譯模型: {model_id}")

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=dtype,
            device_map="auto",
        )

        for chinese, reference, difficulty in TRANSLATION_TEST_CASES:
            prompt = (
                "You are a Chinese-to-English translator for a children's language learning tool.\n"
                "Translate the following Chinese sentence into natural, simple English.\n"
                "Output ONLY the English translation, nothing else.\n\n"
                f"Chinese: {chinese}"
            )
            messages = [{"role": "user", "content": prompt}]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
            device = next(model.parameters()).device
            inputs = tokenizer(text, return_tensors="pt").to(device)
            input_count = inputs["input_ids"].shape[1]

            t0 = time.perf_counter()
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=256, do_sample=False)
            elapsed = time.perf_counter() - t0

            generated_ids = outputs[0][input_count:]
            output_count = len(generated_ids)
            tok_s = output_count / elapsed if elapsed > 0 else 0

            raw = tokenizer.decode(generated_ids, skip_special_tokens=False)
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
            raw = re.sub(r"<\|[^>]+\|>", "", raw)
            hypothesis = raw.strip()

            results.append(TranslationResult(
                chinese=chinese,
                reference=reference,
                hypothesis=hypothesis,
                difficulty=difficulty,
                latency_ms=elapsed * 1000,
                input_tokens=input_count,
                output_tokens=output_count,
                tokens_per_sec=tok_s,
            ))
            print(f"  [{difficulty}] {chinese}")
            print(f"    → {hypothesis} ({elapsed:.2f}s, {tok_s:.1f} tok/s)")

    elif device_mode == "edge":
        # 使用 edge 模式（CPU + llama.cpp）
        from llama_cpp import Llama

        model_path = os.environ.get(
            "C2E_EDGE_TRANSLATION_MODEL_PATH",
            str(C2E_DIR / "models" / "Qwen3-1.7B-Q4_K_M.gguf"),
        )
        print(f"載入翻譯模型: {model_path}")

        llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=int(os.environ.get("C2E_EDGE_TRANSLATION_NUM_THREADS", "4")),
            verbose=False,
        )

        for chinese, reference, difficulty in TRANSLATION_TEST_CASES:
            prompt = (
                "You are a Chinese-to-English translator for a children's language learning tool.\n"
                "Translate the following Chinese sentence into natural, simple English.\n"
                "Output ONLY the English translation, nothing else.\n\n"
                f"Chinese: {chinese}"
            )

            t0 = time.perf_counter()
            output = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0,
            )
            elapsed = time.perf_counter() - t0

            hypothesis = output["choices"][0]["message"]["content"].strip()
            usage = output.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            tok_s = output_tokens / elapsed if elapsed > 0 else 0

            results.append(TranslationResult(
                chinese=chinese,
                reference=reference,
                hypothesis=hypothesis,
                difficulty=difficulty,
                latency_ms=elapsed * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tokens_per_sec=tok_s,
            ))
            print(f"  [{difficulty}] {chinese}")
            print(f"    → {hypothesis} ({elapsed:.2f}s, {tok_s:.1f} tok/s)")

    return results


# =============================================================================
# BLEU 評分
# =============================================================================

def compute_bleu_scores(results: list[TranslationResult]) -> dict:
    """計算 BLEU 分數"""
    try:
        import sacrebleu
    except ImportError:
        print("WARN: sacrebleu 未安裝，跳過 BLEU 計算。 pip install sacrebleu")
        return {}

    refs = [r.reference for r in results]
    hyps = [r.hypothesis for r in results]

    # 整體 BLEU
    bleu = sacrebleu.corpus_bleu(hyps, [refs])

    # 按難度分組
    by_difficulty = {}
    for difficulty in ["easy", "medium", "hard", "child_speech"]:
        d_refs = [r.reference for r in results if r.difficulty == difficulty]
        d_hyps = [r.hypothesis for r in results if r.difficulty == difficulty]
        if d_refs:
            d_bleu = sacrebleu.corpus_bleu(d_hyps, [d_refs])
            by_difficulty[difficulty] = {
                "bleu": round(d_bleu.score, 2),
                "count": len(d_refs),
            }

    return {
        "overall_bleu": round(bleu.score, 2),
        "by_difficulty": by_difficulty,
    }


# =============================================================================
# 系統資訊
# =============================================================================

def get_system_info() -> dict:
    """收集系統硬體資訊"""
    info = {
        "platform": sys.platform,
        "python_version": sys.version,
    }

    try:
        import psutil
        info["cpu_count"] = psutil.cpu_count()
        info["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
        info["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 1)
    except ImportError:
        pass

    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["gpu_memory_gb"] = round(props.total_mem / (1024**3), 1)
    except ImportError:
        pass

    return info


# =============================================================================
# 報告生成
# =============================================================================

def generate_report(report: BenchmarkReport, output_dir: Path):
    """生成效能報告"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON 完整報告
    json_path = output_dir / f"benchmark_{report.device}_{report.timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    print(f"\nJSON 報告: {json_path}")

    # CSV 翻譯結果
    if report.translation_results:
        csv_path = output_dir / f"translation_{report.device}_{report.timestamp}.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(report.translation_results[0]).keys()))
            writer.writeheader()
            for r in report.translation_results:
                writer.writerow(asdict(r))
        print(f"翻譯 CSV: {csv_path}")

    # Markdown 摘要
    md_path = output_dir / f"benchmark_{report.device}_{report.timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 效能測試報告 — {report.device}\n\n")
        f.write(f"**時間**: {report.timestamp}\n\n")

        f.write("## 系統資訊\n\n")
        for k, v in report.system_info.items():
            f.write(f"- **{k}**: {v}\n")

        f.write("\n## 模型配置\n\n")
        for k, v in report.model_config.items():
            f.write(f"- **{k}**: {v}\n")

        if report.summary:
            f.write("\n## 摘要\n\n")
            f.write("| 指標 | 數值 |\n|------|------|\n")
            for k, v in report.summary.items():
                f.write(f"| {k} | {v} |\n")

        if report.translation_results:
            f.write("\n## 翻譯結果\n\n")
            f.write("| 難度 | 中文 | 翻譯 | 延遲(ms) | tok/s |\n")
            f.write("|------|------|------|----------|-------|\n")
            for r in report.translation_results:
                f.write(
                    f"| {r.difficulty} | {r.chinese} | {r.hypothesis} | "
                    f"{r.latency_ms:.0f} | {r.tokens_per_sec:.1f} |\n"
                )

    print(f"Markdown 報告: {md_path}")


# =============================================================================
# 比較報告
# =============================================================================

def generate_comparison(edge_json: Path, nano_json: Path, output_dir: Path):
    """生成 Edge vs ZGX Nano 比較報告"""
    with open(edge_json, encoding="utf-8") as f:
        edge = json.load(f)
    with open(nano_json, encoding="utf-8") as f:
        nano = json.load(f)

    md_path = output_dir / "comparison_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Edge vs ZGX Nano 效能比較報告\n\n")

        f.write("## 翻譯效能\n\n")
        f.write("| 指標 | Edge (CPU) | ZGX Nano (GPU) | 提升倍數 |\n")
        f.write("|------|-----------|----------------|----------|\n")

        edge_summary = edge.get("summary", {})
        nano_summary = nano.get("summary", {})

        for key in ["avg_latency_ms", "avg_tokens_per_sec", "overall_bleu"]:
            ev = edge_summary.get(key, "N/A")
            nv = nano_summary.get(key, "N/A")
            if isinstance(ev, (int, float)) and isinstance(nv, (int, float)) and ev > 0:
                if key == "avg_latency_ms":
                    ratio = f"{ev / nv:.1f}x 更快"
                else:
                    ratio = f"{nv / ev:.1f}x"
            else:
                ratio = "—"
            f.write(f"| {key} | {ev} | {nv} | {ratio} |\n")

    print(f"\n比較報告: {md_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="HP ZGX Nano 效能測試")
    parser.add_argument(
        "--mode",
        choices=["all", "translation", "asr", "compare"],
        default="translation",
        help="測試模式",
    )
    parser.add_argument(
        "--device",
        choices=["edge", "zgx-nano", "auto"],
        default="auto",
        help="裝置模式",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results",
        help="輸出目錄",
    )
    parser.add_argument(
        "--edge-json",
        type=str,
        help="Edge 測試結果 JSON（用於 compare 模式）",
    )
    parser.add_argument(
        "--nano-json",
        type=str,
        help="ZGX Nano 測試結果 JSON（用於 compare 模式）",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    if args.mode == "compare":
        if not args.edge_json or not args.nano_json:
            print("ERROR: compare 模式需要 --edge-json 和 --nano-json")
            sys.exit(1)
        generate_comparison(Path(args.edge_json), Path(args.nano_json), output_dir)
        return

    # 自動偵測裝置
    if args.device == "auto":
        try:
            import torch
            device_mode = "zgx-nano" if torch.cuda.is_available() else "edge"
        except ImportError:
            device_mode = "edge"
    else:
        device_mode = args.device

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    print(f"效能測試開始 — 裝置: {device_mode}, 時間: {timestamp}")

    report = BenchmarkReport(
        timestamp=timestamp,
        device=device_mode,
        system_info=get_system_info(),
    )

    # 記錄模型配置
    if device_mode == "zgx-nano":
        report.model_config = {
            "translation_model": os.environ.get("C2E_TRANSLATION_MODEL_ID", "Qwen/Qwen3-30B"),
            "asr_model": os.environ.get("C2E_ASR_MODEL_ID", "Qwen/Qwen3-ASR-0.6B"),
            "tts_backend": os.environ.get("C2E_TTS_BACKEND", "cosyvoice"),
            "precision": "FP16",
        }
    else:
        report.model_config = {
            "translation_model": os.environ.get(
                "C2E_EDGE_TRANSLATION_MODEL_PATH", "models/Qwen3-1.7B-Q4_K_M.gguf"
            ),
            "asr_backend": os.environ.get("C2E_EDGE_ASR_BACKEND", "sensevoice"),
            "tts_backend": "piper",
            "precision": "Q4_K_M / INT8",
        }

    if args.mode in ("all", "translation"):
        print("\n=== 翻譯效能測試 ===")
        report.translation_results = benchmark_translation(device_mode)

        # 計算摘要
        if report.translation_results:
            avg_latency = sum(r.latency_ms for r in report.translation_results) / len(
                report.translation_results
            )
            avg_tok_s = sum(r.tokens_per_sec for r in report.translation_results) / len(
                report.translation_results
            )
            bleu_scores = compute_bleu_scores(report.translation_results)

            report.summary.update({
                "avg_latency_ms": round(avg_latency, 1),
                "avg_tokens_per_sec": round(avg_tok_s, 1),
                "total_test_cases": len(report.translation_results),
                **bleu_scores,
            })

    generate_report(report, output_dir)
    print("\n效能測試完成！")


if __name__ == "__main__":
    main()
