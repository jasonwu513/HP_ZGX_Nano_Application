#!/usr/bin/env python3
"""
Build game-ready vocabulary CSV from markdown source files.

Parses three markdown vocabulary files (elementary, junior high, senior high),
extracts word entries with Chinese translations, and produces a deduplicated
CSV suitable for Unity game import.

Usage:
    python scripts/build_game_csv.py
"""

import csv
import re
import os
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_FILES = [
    {
        "path": os.path.join(BASE_DIR, "1200-essential-english-words-with-chinese.md"),
        "level": "elementary",
    },
    {
        "path": os.path.join(BASE_DIR, "3000-junior-high-school-words.md"),
        "level": "junior",
    },
    {
        "path": os.path.join(BASE_DIR, "8000-senior-high-school-words.md"),
        "level": "senior",
    },
]

OUTPUT_CSV = os.path.join(BASE_DIR, "game_vocabulary.csv")

# Topics whose words should be flagged as imageable (has_image=1)
IMAGEABLE_TOPICS = {
    # --- elementary (1200-essential-english-words-with-chinese.md) ---
    "Family & People",
    "Body & Health",
    "Food & Drinks",
    "Animals",
    "Colors & Shapes",
    "Clothes & Accessories",
    "House & Home",
    "Transportation & Travel",
    "Places in Town",
    "Jobs & Occupations",
    "Sports & Hobbies",
    "Technology & Communication",
    "Common Nouns (Everyday Things)",
    "Weather & Nature",
    "School & Education",
    # --- junior (3000-junior-high-school-words.md) ---
    "Food, Cooking & Nutrition (Advanced)",
    "Music, Art & Performance",
    "Home & Daily Living (Advanced)",
    "Environment & Ecology",
    "Health, Medicine & Fitness",
    "Travel & Tourism (Advanced)",
    "Technology & Digital Life",
    "Nature & Earth Science",
    "Household & Practical Skills",
    "Sports & Physical Activities (Advanced)",
    # --- senior (8000-senior-high-school-words.md) ---
    "Biology & Life Sciences",
    "Medicine & Health Sciences",
    "Engineering & Architecture",
    "Arts, Music & Cultural Studies",
    "Sports & Competition",
    "Culinary Arts & Gastronomy",
}

# Regex patterns
SECTION_HEADER_RE = re.compile(r"^##\s+\d+\.\s+(.+)$")
TABLE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(.+)\|(.+)\|(.+)\|$")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_markdown(filepath: str, level: str) -> list[dict]:
    """Parse a markdown vocabulary file and return a list of word entries."""
    entries = []
    current_topic = "Unknown"

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            # Check for section header
            header_match = SECTION_HEADER_RE.match(line)
            if header_match:
                current_topic = header_match.group(1).strip()
                continue

            # Check for table data row (skip header and separator rows)
            row_match = TABLE_ROW_RE.match(line)
            if row_match:
                word = row_match.group(2).strip()
                chinese = row_match.group(3).strip()
                definition = row_match.group(4).strip()

                # Determine if this topic is imageable
                has_image = 1 if current_topic in IMAGEABLE_TOPICS else 0

                entries.append({
                    "word": word,
                    "chinese": chinese,
                    "type": current_topic,
                    "definition": definition,
                    "level": level,
                    "has_image": has_image,
                })

    return entries


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove duplicate words (case-insensitive). First occurrence wins."""
    seen = set()
    unique = []
    for entry in entries:
        key = entry["word"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_entries = []

    for source in SOURCE_FILES:
        filepath = source["path"]
        level = source["level"]

        if not os.path.isfile(filepath):
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

        entries = parse_markdown(filepath, level)
        print(f"  Parsed {len(entries):>5} words from {os.path.basename(filepath)} (level={level})")
        all_entries.extend(entries)

    print(f"\n  Total words before dedup: {len(all_entries)}")

    unique_entries = deduplicate(all_entries)
    print(f"  Total words after dedup:  {len(unique_entries)}")
    print(f"  Duplicates removed:       {len(all_entries) - len(unique_entries)}")

    # Count per level
    level_counts = {}
    imageable_count = 0
    for entry in unique_entries:
        level_counts[entry["level"]] = level_counts.get(entry["level"], 0) + 1
        if entry["has_image"]:
            imageable_count += 1

    print("\n  Words per level:")
    for level in ["elementary", "junior", "senior"]:
        print(f"    {level:>12}: {level_counts.get(level, 0)}")
    print(f"\n  Imageable words (has_image=1): {imageable_count}")

    # Write CSV
    fieldnames = ["word", "chinese", "type", "definition", "level", "has_image"]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_entries)

    print(f"\n  Output written to: {OUTPUT_CSV}")
    print(f"  Total rows (excluding header): {len(unique_entries)}")


if __name__ == "__main__":
    print("Building game vocabulary CSV...\n")
    main()
    print("\nDone.")
