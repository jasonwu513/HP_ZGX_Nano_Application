#!/usr/bin/env python3
"""
Flux.1-schnell 教育圖卡生成 Pipeline

讀取 game_vocabulary.csv → 生成 prompt → Flux 生圖
優先處理 elementary 程度、has_image=1 的類別

使用方式:
    # 生成所有 elementary 圖卡
    python image-generation/generate_cards.py

    # 生成指定類別
    python image-generation/generate_cards.py --category "Animals"

    # 生成指定詞彙
    python image-generation/generate_cards.py --word "cat"

    # 使用不同模型
    python image-generation/generate_cards.py --model-path models/FLUX.1-schnell

    # 只生成 prompt（不執行生圖）
    python image-generation/generate_cards.py --dry-run

    # 限制生成數量
    python image-generation/generate_cards.py --limit 10
"""

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VOCAB_CSV = PROJECT_ROOT / "vocabulary" / "game_vocabulary.csv"
OUTPUT_DIR = PROJECT_ROOT / "vocabulary" / "assets" / "images"
PROMPTS_DIR = PROJECT_ROOT / "image-generation" / "prompts"


# =============================================================================
# Prompt 模板 — 童趣卡通風格教育插圖
# =============================================================================

# 基礎風格指令（所有圖片共用）
BASE_STYLE = (
    "cute cartoon illustration for children's educational flashcard, "
    "simple clean design, bright cheerful colors, white background, "
    "kawaii style, friendly and appealing to young children aged 5-8, "
    "no text, no letters, no words, single centered subject, "
    "high quality, sharp details, professional illustration"
)

# 各類別的特殊 prompt 調整
CATEGORY_PROMPTS = {
    "Animals": "a cute cartoon {word}, adorable animal character, simple friendly expression, ",
    "Food & Drinks": "a delicious-looking cartoon {word}, appetizing food illustration, ",
    "Family & People": "a friendly cartoon character representing '{word}', warm family illustration, ",
    "Body & Health": "a cute educational illustration showing '{word}', child-friendly anatomy, ",
    "Clothes & Accessories": "a cute cartoon {word}, fashion illustration for kids, ",
    "Colors & Shapes": "a bright colorful illustration of '{word}', geometric and playful, ",
    "House & Home": "a cozy cartoon illustration of a {word}, home sweet home style, ",
    "School & Education": "a fun cartoon {word}, school-themed illustration, ",
    "Weather & Nature": "a beautiful cartoon illustration of {word} weather/nature, ",
    "Transportation & Travel": "a cute cartoon {word}, vehicle/travel illustration, ",
    "Feelings & Emotions": "a cartoon character expressing '{word}' emotion, expressive face, ",
    "Sports & Hobbies": "a fun cartoon illustration of {word} activity, active and energetic, ",
    "Common Nouns (Everyday Things)": "a simple cute cartoon {word}, everyday object illustration, ",
    "Places in Town": "a cute cartoon illustration of a {word}, town building/place, ",
    "Jobs & Occupations": "a friendly cartoon character as a {word}, occupation illustration, ",
    "Technology & Communication": "a modern cute cartoon {word}, tech illustration for kids, ",
}

# 預設 prompt（無特殊類別時使用）
DEFAULT_CATEGORY_PROMPT = "a cute cartoon illustration of '{word}', "

# 負面提示詞
NEGATIVE_PROMPT = (
    "text, letters, words, watermark, signature, ugly, deformed, "
    "scary, dark, violent, inappropriate, adult content, "
    "blurry, low quality, distorted, extra limbs"
)


@dataclass
class VocabEntry:
    word: str
    chinese: str
    type: str
    definition: str
    level: str
    has_image: bool


def load_vocabulary(
    csv_path: Path,
    category: str | None = None,
    word: str | None = None,
    level: str = "elementary",
    only_needs_image: bool = True,
) -> list[VocabEntry]:
    """載入需要生成圖片的詞彙"""
    entries = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if only_needs_image and row["has_image"].strip() != "1":
                continue
            if level and row["level"].strip() != level:
                continue
            if category and row["type"].strip() != category:
                continue
            if word and row["word"].strip().lower() != word.lower():
                continue

            entries.append(VocabEntry(
                word=row["word"].strip(),
                chinese=row["chinese"].strip(),
                type=row["type"].strip(),
                definition=row["definition"].strip(),
                level=row["level"].strip(),
                has_image=row["has_image"].strip() == "1",
            ))
    return entries


def build_prompt(entry: VocabEntry) -> str:
    """根據詞彙和類別建立 Flux prompt"""
    cat_template = CATEGORY_PROMPTS.get(entry.type, DEFAULT_CATEGORY_PROMPT)
    specific = cat_template.format(word=entry.word)
    return specific + BASE_STYLE


def generate_prompts_file(entries: list[VocabEntry], output_path: Path):
    """將所有 prompt 輸出為 JSON 檔案"""
    prompts = []
    for entry in entries:
        prompts.append({
            "word": entry.word,
            "chinese": entry.chinese,
            "category": entry.type,
            "level": entry.level,
            "prompt": build_prompt(entry),
            "negative_prompt": NEGATIVE_PROMPT,
            "output_filename": f"{entry.type.lower().replace(' & ', '_').replace(' ', '_')}/{entry.word}.png",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"Prompts 已輸出: {output_path} ({len(prompts)} 個)")
    return prompts


def generate_images(prompts: list[dict], model_path: str, output_base: Path, limit: int = 0):
    """使用 Flux.1-schnell 生成圖片"""
    try:
        import torch
        from diffusers import FluxPipeline
    except ImportError:
        print("ERROR: 需要安裝 diffusers 和 torch")
        print("  pip install diffusers[torch] transformers accelerate sentencepiece")
        sys.exit(1)

    print(f"載入 Flux 模型: {model_path}")
    pipe = FluxPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
    )
    # 使用 GPU（ZGX Nano 的統一記憶體）
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    print("Flux 模型載入完成")

    total = len(prompts) if limit <= 0 else min(limit, len(prompts))
    generated = 0
    skipped = 0
    errors = 0

    for i, p in enumerate(prompts[:total]):
        output_path = output_base / p["output_filename"]

        # 跳過已存在的圖片
        if output_path.exists():
            skipped += 1
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            t0 = time.perf_counter()
            image = pipe(
                prompt=p["prompt"],
                num_inference_steps=4,  # schnell 只需要 4 步
                guidance_scale=0.0,     # schnell 不需要 guidance
                height=512,
                width=512,
            ).images[0]
            elapsed = time.perf_counter() - t0

            image.save(output_path)
            generated += 1

            print(
                f"  [{i+1}/{total}] {p['word']} ({p['category']}) "
                f"→ {output_path.name} ({elapsed:.1f}s)"
            )

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{total}] ERROR: {p['word']} — {e}")

    print(f"\n生成完成: {generated} 張, 跳過: {skipped} 張, 錯誤: {errors} 張")
    return generated


# =============================================================================
# 按類別優先順序排序
# =============================================================================

PRIORITY_CATEGORIES = [
    "Animals",
    "Food & Drinks",
    "Family & People",
    "Body & Health",
    "Clothes & Accessories",
    "Colors & Shapes",
    "House & Home",
    "School & Education",
    "Weather & Nature",
    "Transportation & Travel",
    "Feelings & Emotions",
    "Sports & Hobbies",
    "Common Nouns (Everyday Things)",
    "Places in Town",
    "Jobs & Occupations",
    "Technology & Communication",
]


def sort_by_priority(entries: list[VocabEntry]) -> list[VocabEntry]:
    """按優先類別排序"""
    def priority_key(e: VocabEntry) -> int:
        try:
            return PRIORITY_CATEGORIES.index(e.type)
        except ValueError:
            return len(PRIORITY_CATEGORIES)

    return sorted(entries, key=priority_key)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Flux 教育圖卡生成 Pipeline")
    parser.add_argument("--category", type=str, help="指定類別")
    parser.add_argument("--word", type=str, help="指定詞彙")
    parser.add_argument("--level", type=str, default="elementary", help="程度 (default: elementary)")
    parser.add_argument("--model-path", type=str, default="models/FLUX.1-schnell", help="Flux 模型路徑")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="圖片輸出目錄")
    parser.add_argument("--dry-run", action="store_true", help="只生成 prompt，不生圖")
    parser.add_argument("--limit", type=int, default=0, help="限制生成數量")
    args = parser.parse_args()

    print("=== Flux 教育圖卡生成 Pipeline ===\n")

    # 載入詞彙
    entries = load_vocabulary(
        VOCAB_CSV,
        category=args.category,
        word=args.word,
        level=args.level,
    )
    entries = sort_by_priority(entries)

    print(f"共 {len(entries)} 個詞彙需要生成圖片")

    # 統計各類別
    from collections import Counter
    cat_counts = Counter(e.type for e in entries)
    print("\n各類別數量:")
    for cat, count in cat_counts.most_common():
        print(f"  {count:4d}  {cat}")

    # 生成 prompts
    prompts_path = PROMPTS_DIR / "prompts.json"
    prompts = generate_prompts_file(entries, prompts_path)

    if args.dry_run:
        print("\n[DRY RUN] 只生成 prompt，不執行圖片生成")
        # 印出前 5 個範例
        print("\n範例 prompts:")
        for p in prompts[:5]:
            print(f"\n  Word: {p['word']} ({p['chinese']})")
            print(f"  Category: {p['category']}")
            print(f"  Prompt: {p['prompt'][:100]}...")
            print(f"  Output: {p['output_filename']}")
        return

    # 生成圖片
    output_base = Path(args.output)
    model_path = str(PROJECT_ROOT / args.model_path)

    if not Path(model_path).exists():
        # 嘗試 HuggingFace Hub 名稱
        model_path = args.model_path

    generate_images(prompts, model_path, output_base, limit=args.limit)


if __name__ == "__main__":
    main()
