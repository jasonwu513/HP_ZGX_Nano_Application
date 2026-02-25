# Unity Vocabulary Game - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a cross-platform 2D vocabulary learning game in Unity with 5 game modes, 12,200 words, picture support for concrete nouns, and a full progression system.

**Architecture:** Unity Canvas UI game with C# scripts. CSV data loaded at runtime into memory. Local save via JSON + PlayerPrefs. Object Pooling for UI elements. Scenes: MainMenu, GamePlay, Results.

**Tech Stack:** Unity 2022 LTS+, C#, Unity Canvas UI, TextMeshPro, Unity Test Framework (NUnit), Noto Sans TC font.

---

## Phase 1: Data Preparation

### Task 1: Create Enhanced CSV with Chinese Translations

The existing `vocabulary.csv` lacks Chinese translations. We need to parse the markdown files and produce a game-ready CSV.

**Files:**
- Read: `1200-essential-english-words-with-chinese.md`
- Read: `3000-junior-high-school-words.md`
- Read: `8000-senior-high-school-words.md`
- Create: `scripts/build_game_csv.py`
- Create: `game_vocabulary.csv`

**Step 1: Write the Python script to extract data from markdown**

```python
#!/usr/bin/env python3
"""Parse vocabulary markdown files and produce a game-ready CSV."""

import csv
import re
import sys

LEVEL_MAP = {
    "1200-essential-english-words-with-chinese.md": "elementary",
    "3000-junior-high-school-words.md": "junior",
    "8000-senior-high-school-words.md": "senior",
}

# Topics where most words can have images
IMAGEABLE_TOPICS = {
    "Family & People", "Body & Health", "Food & Drinks", "Animals",
    "Colors & Shapes", "Clothes & Accessories", "House & Home",
    "Transportation & Travel", "Places in Town", "Jobs & Occupations",
    "Sports & Hobbies", "Technology & Communication", "Common Nouns (Everyday Things)",
    "Weather & Nature", "School & Education",
    # Junior/Senior topics
    "Animals & Wildlife", "Food & Nutrition", "Clothing & Fashion",
    "Transportation & Vehicles", "Home & Living", "Tools & Equipment",
    "Musical Instruments", "Sports & Recreation",
}

def parse_markdown(filepath):
    """Parse a vocabulary markdown file and yield word entries."""
    current_topic = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Detect topic headers: ## N. Topic Name
            topic_match = re.match(r"^##\s+\d+\.\s+(.+)$", line)
            if topic_match:
                current_topic = topic_match.group(1).strip()
                continue
            # Detect table rows: | N | word | 中文 | definition |
            row_match = re.match(
                r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line
            )
            if row_match and current_topic:
                word = row_match.group(1).strip()
                chinese = row_match.group(2).strip()
                definition = row_match.group(3).strip()
                if word and word != "Word" and chinese != "中文":
                    yield {
                        "word": word,
                        "chinese": chinese,
                        "type": current_topic,
                        "definition": definition,
                    }

def main():
    entries = []
    seen = set()
    for filename, level in LEVEL_MAP.items():
        for entry in parse_markdown(filename):
            key = entry["word"].lower()
            if key in seen:
                continue
            seen.add(key)
            entry["level"] = level
            entry["has_image"] = "1" if entry["type"] in IMAGEABLE_TOPICS else "0"
            entries.append(entry)

    with open("game_vocabulary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["word", "chinese", "type", "definition", "level", "has_image"]
        )
        writer.writeheader()
        writer.writerows(entries)

    print(f"Wrote {len(entries)} entries to game_vocabulary.csv")
    for level in ["elementary", "junior", "senior"]:
        count = sum(1 for e in entries if e["level"] == level)
        imageable = sum(1 for e in entries if e["level"] == level and e["has_image"] == "1")
        print(f"  {level}: {count} words ({imageable} imageable)")

if __name__ == "__main__":
    main()
```

**Step 2: Run the script**

```bash
cd /home/jasonwu513/projects/2026/vocabulary
python3 scripts/build_game_csv.py
```

Expected: `game_vocabulary.csv` created with ~12,200 rows containing word, chinese, type, definition, level, has_image columns.

**Step 3: Verify output**

```bash
head -5 game_vocabulary.csv
wc -l game_vocabulary.csv
```

Expected: Header + ~12,200 data rows. First rows should show elementary words with Chinese translations.

**Step 4: Commit**

```bash
git add scripts/build_game_csv.py game_vocabulary.csv
git commit -m "feat: add game-ready CSV with Chinese translations and image flags"
```

---

## Phase 2: Unity Project Setup

### Task 2: Create Unity Project and Directory Structure

**This task requires Unity Editor (Unity Hub).**

**Step 1: Create new Unity project via Unity Hub**

- Open Unity Hub → New Project
- Template: **2D (URP)** or **2D Core**
- Project name: `VocabularyGame`
- Location: `/home/jasonwu513/projects/2026/vocabulary/` (creates `VocabularyGame/` subfolder)
- Unity version: **2022.3 LTS** or newer

**Step 2: Create folder structure inside Unity project**

```bash
cd /home/jasonwu513/projects/2026/vocabulary/VocabularyGame/Assets
mkdir -p Scripts/Core Scripts/GameModes Scripts/UI Scripts/Progress Scripts/Utils
mkdir -p Data Images Prefabs Resources/Fonts Resources/Sprites
mkdir -p Tests/EditMode Tests/PlayMode
```

**Step 3: Copy game CSV into Unity project**

```bash
cp /home/jasonwu513/projects/2026/vocabulary/game_vocabulary.csv \
   /home/jasonwu513/projects/2026/vocabulary/VocabularyGame/Assets/Data/vocabulary.csv
```

**Step 4: Install TextMeshPro**

In Unity Editor: Window → TextMeshPro → Import TMP Essential Resources

**Step 5: Download and import Noto Sans TC font**

- Download from https://fonts.google.com/noto/specimen/Noto+Sans+TC
- Place `.ttf` file in `Assets/Resources/Fonts/`
- In Unity: right-click the font → Create → TextMeshPro → Font Asset
- Configure: Atlas size 4096x4096, include CJK character ranges

**Step 6: Create three scenes**

In Unity Editor:
- File → New Scene → Save as `Assets/Scenes/MainMenu.unity`
- File → New Scene → Save as `Assets/Scenes/GamePlay.unity`
- File → New Scene → Save as `Assets/Scenes/Results.unity`
- Add all three to Build Settings (File → Build Settings → Add Open Scenes)

**Step 7: Commit Unity project**

```bash
git add VocabularyGame/
git commit -m "feat: initialize Unity project with folder structure and scenes"
```

---

## Phase 3: Core Data System

### Task 3: VocabularyEntry Data Model

**Files:**
- Create: `Assets/Scripts/Core/VocabularyEntry.cs`
- Test: `Assets/Tests/EditMode/VocabularyEntryTests.cs`

**Step 1: Create the Edit Mode test assembly**

Create `Assets/Tests/EditMode/EditModeTests.asmdef`:
```json
{
    "name": "EditModeTests",
    "rootNamespace": "",
    "references": ["VocabularyGame"],
    "includePlatforms": ["Editor"],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": true,
    "precompiledReferences": ["nunit.framework.dll"],
    "autoReferenced": false,
    "defineConstraints": ["UNITY_INCLUDE_TESTS"],
    "versionDefines": [],
    "noEngineReferences": false
}
```

Create `Assets/Scripts/VocabularyGame.asmdef`:
```json
{
    "name": "VocabularyGame",
    "rootNamespace": "VocabularyGame",
    "references": [],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": [],
    "versionDefines": [],
    "noEngineReferences": false
}
```

**Step 2: Write the failing test**

`Assets/Tests/EditMode/VocabularyEntryTests.cs`:
```csharp
using NUnit.Framework;
using VocabularyGame.Core;

namespace VocabularyGame.Tests
{
    public class VocabularyEntryTests
    {
        [Test]
        public void CanCreateEntry()
        {
            var entry = new VocabularyEntry
            {
                word = "apple",
                chinese = "蘋果",
                type = "Food & Drinks",
                definition = "a round fruit",
                level = WordLevel.Elementary,
                hasImage = true
            };

            Assert.AreEqual("apple", entry.word);
            Assert.AreEqual("蘋果", entry.chinese);
            Assert.AreEqual(WordLevel.Elementary, entry.level);
            Assert.IsTrue(entry.hasImage);
        }

        [Test]
        public void LevelFromString_ParsesCorrectly()
        {
            Assert.AreEqual(WordLevel.Elementary, VocabularyEntry.ParseLevel("elementary"));
            Assert.AreEqual(WordLevel.Junior, VocabularyEntry.ParseLevel("junior"));
            Assert.AreEqual(WordLevel.Senior, VocabularyEntry.ParseLevel("senior"));
        }
    }
}
```

**Step 3: Run test — expect FAIL**

In Unity: Window → General → Test Runner → EditMode → Run All
Expected: Compilation error — `VocabularyEntry` and `WordLevel` not found.

**Step 4: Implement VocabularyEntry**

`Assets/Scripts/Core/VocabularyEntry.cs`:
```csharp
namespace VocabularyGame.Core
{
    public enum WordLevel
    {
        Elementary,
        Junior,
        Senior
    }

    [System.Serializable]
    public class VocabularyEntry
    {
        public string word;
        public string chinese;
        public string type;
        public string definition;
        public WordLevel level;
        public bool hasImage;
        public string imagePath;

        public static WordLevel ParseLevel(string levelStr)
        {
            return levelStr.ToLower() switch
            {
                "elementary" => WordLevel.Elementary,
                "junior" => WordLevel.Junior,
                "senior" => WordLevel.Senior,
                _ => WordLevel.Elementary
            };
        }
    }
}
```

**Step 5: Run test — expect PASS**

In Unity Test Runner: Run All → both tests should pass.

**Step 6: Commit**

```bash
git add Assets/Scripts/Core/VocabularyEntry.cs Assets/Tests/
git commit -m "feat: add VocabularyEntry data model with level parsing"
```

---

### Task 4: CSV DataLoader

**Files:**
- Create: `Assets/Scripts/Core/DataLoader.cs`
- Test: `Assets/Tests/EditMode/DataLoaderTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/DataLoaderTests.cs`:
```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Core;

namespace VocabularyGame.Tests
{
    public class DataLoaderTests
    {
        private const string TestCsv =
            "word,chinese,type,definition,level,has_image\n" +
            "apple,蘋果,Food & Drinks,a round fruit,elementary,1\n" +
            "dog,狗,Animals,a common pet animal,elementary,1\n" +
            "freedom,自由,Abstract Nouns,the state of being free,senior,0\n";

        [Test]
        public void ParseCsv_ReturnsCorrectCount()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            Assert.AreEqual(3, entries.Count);
        }

        [Test]
        public void ParseCsv_FirstEntryCorrect()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            Assert.AreEqual("apple", entries[0].word);
            Assert.AreEqual("蘋果", entries[0].chinese);
            Assert.AreEqual("Food & Drinks", entries[0].type);
            Assert.AreEqual(WordLevel.Elementary, entries[0].level);
            Assert.IsTrue(entries[0].hasImage);
        }

        [Test]
        public void ParseCsv_HandlesNoImage()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            Assert.IsFalse(entries[2].hasImage);
            Assert.AreEqual(WordLevel.Senior, entries[2].level);
        }

        [Test]
        public void GetWordsByLevel_FiltersCorrectly()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            var elementary = DataLoader.FilterByLevel(entries, WordLevel.Elementary);
            Assert.AreEqual(2, elementary.Count);
        }

        [Test]
        public void GetWordsByTopic_FiltersCorrectly()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            var food = DataLoader.FilterByTopic(entries, "Food & Drinks");
            Assert.AreEqual(1, food.Count);
            Assert.AreEqual("apple", food[0].word);
        }

        [Test]
        public void GetImageableWords_FiltersCorrectly()
        {
            List<VocabularyEntry> entries = DataLoader.ParseCsvString(TestCsv);
            var imageable = DataLoader.FilterImageable(entries);
            Assert.AreEqual(2, imageable.Count);
        }
    }
}
```

**Step 2: Run test — expect FAIL**

Expected: Compilation error — `DataLoader` not found.

**Step 3: Implement DataLoader**

`Assets/Scripts/Core/DataLoader.cs`:
```csharp
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace VocabularyGame.Core
{
    public static class DataLoader
    {
        public static List<VocabularyEntry> LoadFromResources(string resourcePath = "Data/vocabulary")
        {
            TextAsset csvFile = Resources.Load<TextAsset>(resourcePath);
            if (csvFile == null)
            {
                Debug.LogError($"Could not load vocabulary CSV from Resources/{resourcePath}");
                return new List<VocabularyEntry>();
            }
            return ParseCsvString(csvFile.text);
        }

        public static List<VocabularyEntry> ParseCsvString(string csvText)
        {
            var entries = new List<VocabularyEntry>();
            using var reader = new StringReader(csvText);

            // Skip header
            string header = reader.ReadLine();
            if (header == null) return entries;

            string line;
            while ((line = reader.ReadLine()) != null)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;

                string[] fields = ParseCsvLine(line);
                if (fields.Length < 6) continue;

                entries.Add(new VocabularyEntry
                {
                    word = fields[0].Trim(),
                    chinese = fields[1].Trim(),
                    type = fields[2].Trim(),
                    definition = fields[3].Trim(),
                    level = VocabularyEntry.ParseLevel(fields[4].Trim()),
                    hasImage = fields[5].Trim() == "1"
                });
            }
            return entries;
        }

        private static string[] ParseCsvLine(string line)
        {
            var fields = new List<string>();
            bool inQuotes = false;
            var current = new System.Text.StringBuilder();

            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (c == '"')
                {
                    inQuotes = !inQuotes;
                }
                else if (c == ',' && !inQuotes)
                {
                    fields.Add(current.ToString());
                    current.Clear();
                }
                else
                {
                    current.Append(c);
                }
            }
            fields.Add(current.ToString());
            return fields.ToArray();
        }

        public static List<VocabularyEntry> FilterByLevel(
            List<VocabularyEntry> entries, WordLevel level)
        {
            return entries.Where(e => e.level == level).ToList();
        }

        public static List<VocabularyEntry> FilterByTopic(
            List<VocabularyEntry> entries, string topic)
        {
            return entries.Where(e => e.type == topic).ToList();
        }

        public static List<VocabularyEntry> FilterImageable(
            List<VocabularyEntry> entries)
        {
            return entries.Where(e => e.hasImage).ToList();
        }

        public static List<string> GetTopicsForLevel(
            List<VocabularyEntry> entries, WordLevel level)
        {
            return entries
                .Where(e => e.level == level)
                .Select(e => e.type)
                .Distinct()
                .OrderBy(t => t)
                .ToList();
        }
    }
}
```

**Step 4: Run test — expect PASS**

All 6 tests should pass.

**Step 5: Commit**

```bash
git add Assets/Scripts/Core/DataLoader.cs Assets/Tests/EditMode/DataLoaderTests.cs
git commit -m "feat: add CSV DataLoader with filtering methods"
```

---

### Task 5: PlayerProgress Save/Load System

**Files:**
- Create: `Assets/Scripts/Progress/PlayerProgress.cs`
- Create: `Assets/Scripts/Progress/SaveManager.cs`
- Test: `Assets/Tests/EditMode/PlayerProgressTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/PlayerProgressTests.cs`:
```csharp
using NUnit.Framework;
using VocabularyGame.Progress;

namespace VocabularyGame.Tests
{
    public class PlayerProgressTests
    {
        [Test]
        public void NewProgress_HasDefaultValues()
        {
            var progress = new PlayerProgress();
            Assert.AreEqual(1, progress.playerLevel);
            Assert.AreEqual(0, progress.totalXP);
            Assert.AreEqual(0, progress.dailyStreak);
        }

        [Test]
        public void GetMastery_ReturnsZeroForUnknownWord()
        {
            var progress = new PlayerProgress();
            Assert.AreEqual(0, progress.GetMastery("apple"));
        }

        [Test]
        public void SetMastery_StoresValue()
        {
            var progress = new PlayerProgress();
            progress.SetMastery("apple", 3);
            Assert.AreEqual(3, progress.GetMastery("apple"));
        }

        [Test]
        public void SetMastery_ClampsToRange()
        {
            var progress = new PlayerProgress();
            progress.SetMastery("apple", 7);
            Assert.AreEqual(5, progress.GetMastery("apple"));
            progress.SetMastery("apple", -1);
            Assert.AreEqual(0, progress.GetMastery("apple"));
        }

        [Test]
        public void RecordAnswer_Correct_IncreasesStats()
        {
            var progress = new PlayerProgress();
            progress.RecordAnswer("apple", true);
            Assert.AreEqual(1, progress.GetCorrectCount("apple"));
            Assert.AreEqual(0, progress.GetWrongCount("apple"));
            Assert.AreEqual(1, progress.GetMastery("apple"));
        }

        [Test]
        public void RecordAnswer_Wrong_IncreasesWrongCount()
        {
            var progress = new PlayerProgress();
            progress.SetMastery("apple", 3);
            progress.RecordAnswer("apple", false);
            Assert.AreEqual(0, progress.GetCorrectCount("apple"));
            Assert.AreEqual(1, progress.GetWrongCount("apple"));
            Assert.AreEqual(2, progress.GetMastery("apple"));
        }

        [Test]
        public void RecordAnswer_Wrong_DoesNotGoBelowZero()
        {
            var progress = new PlayerProgress();
            progress.RecordAnswer("apple", false);
            Assert.AreEqual(0, progress.GetMastery("apple"));
        }

        [Test]
        public void SerializeAndDeserialize_Roundtrip()
        {
            var progress = new PlayerProgress();
            progress.totalXP = 500;
            progress.playerLevel = 5;
            progress.SetMastery("apple", 3);
            progress.RecordAnswer("dog", true);

            string json = progress.ToJson();
            var loaded = PlayerProgress.FromJson(json);

            Assert.AreEqual(500, loaded.totalXP);
            Assert.AreEqual(5, loaded.playerLevel);
            Assert.AreEqual(3, loaded.GetMastery("apple"));
            Assert.AreEqual(1, loaded.GetCorrectCount("dog"));
        }

        [Test]
        public void UnlockAchievement_Works()
        {
            var progress = new PlayerProgress();
            Assert.IsFalse(progress.IsAchievementUnlocked("first_step"));
            progress.UnlockAchievement("first_step");
            Assert.IsTrue(progress.IsAchievementUnlocked("first_step"));
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement PlayerProgress**

`Assets/Scripts/Progress/PlayerProgress.cs`:
```csharp
using System.Collections.Generic;
using UnityEngine;

namespace VocabularyGame.Progress
{
    [System.Serializable]
    public class PlayerProgress
    {
        public int playerLevel = 1;
        public int totalXP = 0;
        public int dailyStreak = 0;
        public string lastPlayDate = "";

        // Serializable wrappers for Dictionary (Unity JSON doesn't support Dictionary)
        public List<string> masteryKeys = new();
        public List<int> masteryValues = new();
        public List<string> correctKeys = new();
        public List<int> correctValues = new();
        public List<string> wrongKeys = new();
        public List<int> wrongValues = new();
        public List<string> unlockedAchievements = new();

        // Runtime dictionaries (rebuilt from lists)
        [System.NonSerialized] private Dictionary<string, int> _mastery;
        [System.NonSerialized] private Dictionary<string, int> _correct;
        [System.NonSerialized] private Dictionary<string, int> _wrong;

        private Dictionary<string, int> Mastery
        {
            get
            {
                if (_mastery == null) RebuildDictionaries();
                return _mastery;
            }
        }

        private Dictionary<string, int> Correct
        {
            get
            {
                if (_correct == null) RebuildDictionaries();
                return _correct;
            }
        }

        private Dictionary<string, int> Wrong
        {
            get
            {
                if (_wrong == null) RebuildDictionaries();
                return _wrong;
            }
        }

        private void RebuildDictionaries()
        {
            _mastery = new Dictionary<string, int>();
            for (int i = 0; i < masteryKeys.Count && i < masteryValues.Count; i++)
                _mastery[masteryKeys[i]] = masteryValues[i];

            _correct = new Dictionary<string, int>();
            for (int i = 0; i < correctKeys.Count && i < correctValues.Count; i++)
                _correct[correctKeys[i]] = correctValues[i];

            _wrong = new Dictionary<string, int>();
            for (int i = 0; i < wrongKeys.Count && i < wrongValues.Count; i++)
                _wrong[wrongKeys[i]] = wrongValues[i];
        }

        private void SyncToLists()
        {
            masteryKeys = new List<string>(Mastery.Keys);
            masteryValues = new List<int>(Mastery.Values);
            correctKeys = new List<string>(Correct.Keys);
            correctValues = new List<int>(Correct.Values);
            wrongKeys = new List<string>(Wrong.Keys);
            wrongValues = new List<int>(Wrong.Values);
        }

        public int GetMastery(string word)
        {
            return Mastery.TryGetValue(word, out int val) ? val : 0;
        }

        public void SetMastery(string word, int level)
        {
            Mastery[word] = Mathf.Clamp(level, 0, 5);
        }

        public int GetCorrectCount(string word)
        {
            return Correct.TryGetValue(word, out int val) ? val : 0;
        }

        public int GetWrongCount(string word)
        {
            return Wrong.TryGetValue(word, out int val) ? val : 0;
        }

        public void RecordAnswer(string word, bool correct)
        {
            if (correct)
            {
                Correct[word] = GetCorrectCount(word) + 1;
                int current = GetMastery(word);
                SetMastery(word, current + 1);
            }
            else
            {
                Wrong[word] = GetWrongCount(word) + 1;
                int current = GetMastery(word);
                if (current > 0) SetMastery(word, current - 1);
            }
        }

        public bool IsAchievementUnlocked(string id)
        {
            return unlockedAchievements.Contains(id);
        }

        public void UnlockAchievement(string id)
        {
            if (!unlockedAchievements.Contains(id))
                unlockedAchievements.Add(id);
        }

        public string ToJson()
        {
            SyncToLists();
            return JsonUtility.ToJson(this, true);
        }

        public static PlayerProgress FromJson(string json)
        {
            var progress = JsonUtility.FromJson<PlayerProgress>(json);
            progress.RebuildDictionaries();
            return progress;
        }
    }
}
```

**Step 4: Run tests — expect PASS**

All 9 tests should pass.

**Step 5: Implement SaveManager**

`Assets/Scripts/Progress/SaveManager.cs`:
```csharp
using UnityEngine;

namespace VocabularyGame.Progress
{
    public static class SaveManager
    {
        private const string SaveKey = "player_progress";

        public static void Save(PlayerProgress progress)
        {
            string json = progress.ToJson();
            PlayerPrefs.SetString(SaveKey, json);
            PlayerPrefs.Save();
        }

        public static PlayerProgress Load()
        {
            if (!PlayerPrefs.HasKey(SaveKey))
                return new PlayerProgress();

            string json = PlayerPrefs.GetString(SaveKey);
            return PlayerProgress.FromJson(json);
        }

        public static void DeleteSave()
        {
            PlayerPrefs.DeleteKey(SaveKey);
        }
    }
}
```

**Step 6: Commit**

```bash
git add Assets/Scripts/Progress/ Assets/Tests/EditMode/PlayerProgressTests.cs
git commit -m "feat: add PlayerProgress save/load system with JSON serialization"
```

---

### Task 6: XP and Leveling System

**Files:**
- Create: `Assets/Scripts/Progress/XPSystem.cs`
- Test: `Assets/Tests/EditMode/XPSystemTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/XPSystemTests.cs`:
```csharp
using NUnit.Framework;
using VocabularyGame.Progress;

namespace VocabularyGame.Tests
{
    public class XPSystemTests
    {
        [Test]
        public void BaseXP_CorrectAnswer()
        {
            Assert.AreEqual(10, XPSystem.CalculateXP(true, 0));
        }

        [Test]
        public void ComboBonus_AddsCorrectly()
        {
            Assert.AreEqual(15, XPSystem.CalculateXP(true, 1));
            Assert.AreEqual(20, XPSystem.CalculateXP(true, 2));
            Assert.AreEqual(60, XPSystem.CalculateXP(true, 10)); // capped at +50
        }

        [Test]
        public void WrongAnswer_ZeroXP()
        {
            Assert.AreEqual(0, XPSystem.CalculateXP(false, 5));
        }

        [Test]
        public void XPForLevel_IncreasesWithLevel()
        {
            int xp1 = XPSystem.XPRequiredForLevel(2);
            int xp2 = XPSystem.XPRequiredForLevel(10);
            Assert.Greater(xp2, xp1);
        }

        [Test]
        public void GetLevel_FromTotalXP()
        {
            Assert.AreEqual(1, XPSystem.GetLevelFromXP(0));
            Assert.AreEqual(1, XPSystem.GetLevelFromXP(50));
            Assert.AreEqual(2, XPSystem.GetLevelFromXP(100));
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement XPSystem**

`Assets/Scripts/Progress/XPSystem.cs`:
```csharp
using UnityEngine;

namespace VocabularyGame.Progress
{
    public static class XPSystem
    {
        private const int BaseXP = 10;
        private const int ComboBonus = 5;
        private const int MaxComboBonus = 50;
        private const int DailyChallengeBonus = 100;
        private const int BaseXPPerLevel = 100;

        public static int CalculateXP(bool correct, int comboCount)
        {
            if (!correct) return 0;
            int bonus = Mathf.Min(comboCount * ComboBonus, MaxComboBonus);
            return BaseXP + bonus;
        }

        public static int XPRequiredForLevel(int level)
        {
            // Level 2 = 100 XP, Level 3 = 220, etc. (quadratic growth)
            if (level <= 1) return 0;
            return BaseXPPerLevel * (level - 1) + 20 * (level - 1) * (level - 2) / 2;
        }

        public static int GetLevelFromXP(int totalXP)
        {
            int level = 1;
            while (level < 50 && totalXP >= XPRequiredForLevel(level + 1))
                level++;
            return level;
        }

        public static float GetLevelProgress(int totalXP)
        {
            int currentLevel = GetLevelFromXP(totalXP);
            if (currentLevel >= 50) return 1f;
            int currentLevelXP = XPRequiredForLevel(currentLevel);
            int nextLevelXP = XPRequiredForLevel(currentLevel + 1);
            return (float)(totalXP - currentLevelXP) / (nextLevelXP - currentLevelXP);
        }
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add Assets/Scripts/Progress/XPSystem.cs Assets/Tests/EditMode/XPSystemTests.cs
git commit -m "feat: add XP and leveling system"
```

---

## Phase 4: Game Manager and Scene Navigation

### Task 7: GameManager Singleton

**Files:**
- Create: `Assets/Scripts/Core/GameManager.cs`

**Step 1: Implement GameManager**

`Assets/Scripts/Core/GameManager.cs`:
```csharp
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using VocabularyGame.Progress;

namespace VocabularyGame.Core
{
    public enum GameMode
    {
        Quiz,
        Matching,
        Spelling,
        Picture,
        Flashcard
    }

    public class GameManager : MonoBehaviour
    {
        public static GameManager Instance { get; private set; }

        // Current session settings
        public WordLevel SelectedLevel { get; set; } = WordLevel.Elementary;
        public GameMode SelectedMode { get; set; } = GameMode.Quiz;
        public string SelectedTopic { get; set; } = "All";
        public int QuestionsPerRound { get; set; } = 10;

        // Data
        public List<VocabularyEntry> AllWords { get; private set; }
        public PlayerProgress Progress { get; private set; }

        // Settings
        public bool SoundEnabled { get; set; } = true;
        public bool TimerEnabled { get; set; } = false;
        public int QuizDirection { get; set; } = 0; // 0=EN→CN, 1=CN→EN, 2=Def→Word

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            LoadData();
            LoadProgress();
        }

        private void LoadData()
        {
            AllWords = DataLoader.LoadFromResources();
            Debug.Log($"Loaded {AllWords.Count} vocabulary entries");
        }

        private void LoadProgress()
        {
            Progress = SaveManager.Load();
        }

        public void SaveProgress()
        {
            SaveManager.Save(Progress);
        }

        public List<VocabularyEntry> GetCurrentWordSet()
        {
            var filtered = DataLoader.FilterByLevel(AllWords, SelectedLevel);
            if (SelectedTopic != "All")
                filtered = DataLoader.FilterByTopic(filtered, SelectedTopic);
            return filtered;
        }

        public List<VocabularyEntry> GetImageableWords()
        {
            var filtered = GetCurrentWordSet();
            return DataLoader.FilterImageable(filtered);
        }

        public void LoadScene(string sceneName)
        {
            SceneManager.LoadScene(sceneName);
        }

        public void GoToMainMenu()
        {
            LoadScene("MainMenu");
        }

        public void StartGame()
        {
            LoadScene("GamePlay");
        }

        public void ShowResults()
        {
            LoadScene("Results");
        }
    }
}
```

**Step 2: In Unity Editor — set up GameManager**

- Open MainMenu scene
- Create empty GameObject → name it "GameManager"
- Attach `GameManager.cs` script to it
- Also move `vocabulary.csv` to `Assets/Resources/Data/` folder (so `Resources.Load` works)

**Step 3: Commit**

```bash
git add Assets/Scripts/Core/GameManager.cs
git commit -m "feat: add GameManager singleton with scene navigation"
```

---

## Phase 5: Quiz Mode (First Playable Game Mode)

### Task 8: Quiz Mode Logic

**Files:**
- Create: `Assets/Scripts/GameModes/QuizMode.cs`
- Test: `Assets/Tests/EditMode/QuizModeTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/QuizModeTests.cs`:
```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Core;
using VocabularyGame.GameModes;

namespace VocabularyGame.Tests
{
    public class QuizModeTests
    {
        private List<VocabularyEntry> _testWords;

        [SetUp]
        public void Setup()
        {
            _testWords = new List<VocabularyEntry>
            {
                new() { word = "apple", chinese = "蘋果", type = "Food", definition = "a round fruit", level = WordLevel.Elementary },
                new() { word = "dog", chinese = "狗", type = "Animals", definition = "a pet animal", level = WordLevel.Elementary },
                new() { word = "cat", chinese = "貓", type = "Animals", definition = "a small furry pet", level = WordLevel.Elementary },
                new() { word = "book", chinese = "書", type = "Common Nouns", definition = "pages bound together", level = WordLevel.Elementary },
                new() { word = "house", chinese = "房子", type = "House", definition = "a building to live in", level = WordLevel.Elementary },
            };
        }

        [Test]
        public void GenerateQuestion_ReturnsQuestionWithFourOptions()
        {
            var logic = new QuizLogic(_testWords, 0);
            QuizQuestion q = logic.GenerateQuestion();

            Assert.IsNotNull(q);
            Assert.IsNotNull(q.correctEntry);
            Assert.AreEqual(4, q.options.Count);
        }

        [Test]
        public void GenerateQuestion_CorrectAnswerIsInOptions()
        {
            var logic = new QuizLogic(_testWords, 0);
            QuizQuestion q = logic.GenerateQuestion();

            Assert.Contains(q.correctEntry.chinese, q.options);
        }

        [Test]
        public void GenerateQuestion_OptionsAreUnique()
        {
            var logic = new QuizLogic(_testWords, 0);
            QuizQuestion q = logic.GenerateQuestion();

            var unique = new HashSet<string>(q.options);
            Assert.AreEqual(4, unique.Count);
        }

        [Test]
        public void CheckAnswer_Correct_ReturnsTrue()
        {
            var logic = new QuizLogic(_testWords, 0);
            QuizQuestion q = logic.GenerateQuestion();

            bool result = logic.CheckAnswer(q, q.correctEntry.chinese);
            Assert.IsTrue(result);
        }

        [Test]
        public void CheckAnswer_Wrong_ReturnsFalse()
        {
            var logic = new QuizLogic(_testWords, 0);
            QuizQuestion q = logic.GenerateQuestion();

            bool result = logic.CheckAnswer(q, "wrong_answer");
            Assert.IsFalse(result);
        }

        [Test]
        public void RoundProgress_TracksCorrectly()
        {
            var logic = new QuizLogic(_testWords, 0, questionsPerRound: 3);

            Assert.AreEqual(0, logic.CurrentQuestionIndex);
            Assert.AreEqual(3, logic.TotalQuestions);
            Assert.IsFalse(logic.IsRoundComplete);

            logic.GenerateQuestion();
            logic.AdvanceQuestion();
            Assert.AreEqual(1, logic.CurrentQuestionIndex);

            logic.GenerateQuestion();
            logic.AdvanceQuestion();
            logic.GenerateQuestion();
            logic.AdvanceQuestion();
            Assert.IsTrue(logic.IsRoundComplete);
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement QuizLogic (pure logic, no MonoBehaviour)**

`Assets/Scripts/GameModes/QuizLogic.cs`:
```csharp
using System.Collections.Generic;
using System.Linq;
using VocabularyGame.Core;

namespace VocabularyGame.GameModes
{
    public class QuizQuestion
    {
        public VocabularyEntry correctEntry;
        public string prompt;           // The question text shown
        public List<string> options;    // 4 answer options
    }

    public class QuizLogic
    {
        private readonly List<VocabularyEntry> _wordPool;
        private readonly List<VocabularyEntry> _roundWords;
        private readonly int _direction; // 0=EN→CN, 1=CN→EN, 2=Def→Word

        public int CurrentQuestionIndex { get; private set; }
        public int TotalQuestions { get; }
        public int CorrectCount { get; private set; }
        public int ComboCount { get; private set; }
        public int MaxCombo { get; private set; }
        public bool IsRoundComplete => CurrentQuestionIndex >= TotalQuestions;

        public QuizLogic(List<VocabularyEntry> wordPool, int direction, int questionsPerRound = 10)
        {
            _wordPool = new List<VocabularyEntry>(wordPool);
            _direction = direction;
            TotalQuestions = System.Math.Min(questionsPerRound, _wordPool.Count);
            CurrentQuestionIndex = 0;
            CorrectCount = 0;
            ComboCount = 0;
            MaxCombo = 0;

            // Shuffle and pick words for this round
            var rng = new System.Random();
            _roundWords = _wordPool.OrderBy(_ => rng.Next()).Take(TotalQuestions).ToList();
        }

        public QuizQuestion GenerateQuestion()
        {
            if (IsRoundComplete) return null;

            var correct = _roundWords[CurrentQuestionIndex];
            var distractors = _wordPool
                .Where(w => w.word != correct.word)
                .OrderBy(_ => System.Guid.NewGuid())
                .Take(3)
                .ToList();

            var question = new QuizQuestion { correctEntry = correct };

            switch (_direction)
            {
                case 0: // EN→CN: show English, pick Chinese
                    question.prompt = correct.word;
                    question.options = distractors.Select(d => d.chinese).ToList();
                    question.options.Insert(new System.Random().Next(4), correct.chinese);
                    break;
                case 1: // CN→EN: show Chinese, pick English
                    question.prompt = correct.chinese;
                    question.options = distractors.Select(d => d.word).ToList();
                    question.options.Insert(new System.Random().Next(4), correct.word);
                    break;
                case 2: // Def→Word: show definition, pick word
                    question.prompt = correct.definition;
                    question.options = distractors.Select(d => d.word).ToList();
                    question.options.Insert(new System.Random().Next(4), correct.word);
                    break;
            }

            // Ensure exactly 4 options
            while (question.options.Count > 4)
                question.options.RemoveAt(question.options.Count - 1);

            return question;
        }

        public bool CheckAnswer(QuizQuestion question, string selectedAnswer)
        {
            string correctAnswer = _direction switch
            {
                0 => question.correctEntry.chinese,
                1 => question.correctEntry.word,
                2 => question.correctEntry.word,
                _ => question.correctEntry.chinese
            };

            bool isCorrect = selectedAnswer == correctAnswer;

            if (isCorrect)
            {
                CorrectCount++;
                ComboCount++;
                if (ComboCount > MaxCombo) MaxCombo = ComboCount;
            }
            else
            {
                ComboCount = 0;
            }

            return isCorrect;
        }

        public void AdvanceQuestion()
        {
            CurrentQuestionIndex++;
        }
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add Assets/Scripts/GameModes/QuizLogic.cs Assets/Tests/EditMode/QuizModeTests.cs
git commit -m "feat: add QuizLogic with question generation and answer checking"
```

---

### Task 9: Quiz Mode MonoBehaviour + UI

**Files:**
- Create: `Assets/Scripts/GameModes/QuizMode.cs`
- Create: `Assets/Scripts/UI/GameplayUI.cs`

**Step 1: Implement QuizMode MonoBehaviour**

`Assets/Scripts/GameModes/QuizMode.cs`:
```csharp
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using VocabularyGame.Core;
using VocabularyGame.Progress;

namespace VocabularyGame.GameModes
{
    public class QuizMode : MonoBehaviour
    {
        [Header("UI References")]
        [SerializeField] private TextMeshProUGUI questionText;
        [SerializeField] private TextMeshProUGUI progressText;
        [SerializeField] private TextMeshProUGUI comboText;
        [SerializeField] private Button[] optionButtons;
        [SerializeField] private TextMeshProUGUI[] optionTexts;
        [SerializeField] private Image[] optionImages;
        [SerializeField] private GameObject feedbackPanel;
        [SerializeField] private TextMeshProUGUI feedbackText;
        [SerializeField] private float feedbackDelay = 1.5f;

        private QuizLogic _logic;
        private QuizQuestion _currentQuestion;
        private bool _waitingForNext;

        private readonly Color _normalColor = new(0.95f, 0.95f, 0.95f);
        private readonly Color _correctColor = new(0.6f, 0.9f, 0.6f);
        private readonly Color _wrongColor = new(0.9f, 0.6f, 0.6f);

        private void Start()
        {
            var gm = GameManager.Instance;
            var words = gm.GetCurrentWordSet();
            _logic = new QuizLogic(words, gm.QuizDirection, gm.QuestionsPerRound);

            for (int i = 0; i < optionButtons.Length; i++)
            {
                int index = i;
                optionButtons[i].onClick.AddListener(() => OnOptionClicked(index));
            }

            feedbackPanel.SetActive(false);
            ShowNextQuestion();
        }

        private void ShowNextQuestion()
        {
            if (_logic.IsRoundComplete)
            {
                GameManager.Instance.ShowResults();
                return;
            }

            _currentQuestion = _logic.GenerateQuestion();
            questionText.text = _currentQuestion.prompt;
            progressText.text = $"{_logic.CurrentQuestionIndex + 1} / {_logic.TotalQuestions}";
            comboText.text = _logic.ComboCount > 1 ? $"Combo x{_logic.ComboCount}" : "";

            for (int i = 0; i < optionButtons.Length; i++)
            {
                optionTexts[i].text = _currentQuestion.options[i];
                optionImages[i].color = _normalColor;
                optionButtons[i].interactable = true;
            }

            feedbackPanel.SetActive(false);
            _waitingForNext = false;
        }

        private void OnOptionClicked(int index)
        {
            if (_waitingForNext) return;
            _waitingForNext = true;

            string selected = _currentQuestion.options[index];
            bool correct = _logic.CheckAnswer(_currentQuestion, selected);

            // Record to progress
            var gm = GameManager.Instance;
            gm.Progress.RecordAnswer(_currentQuestion.correctEntry.word, correct);

            // Add XP
            if (correct)
            {
                int xp = XPSystem.CalculateXP(true, _logic.ComboCount - 1);
                gm.Progress.totalXP += xp;
                gm.Progress.playerLevel = XPSystem.GetLevelFromXP(gm.Progress.totalXP);
            }

            // Visual feedback
            string correctAnswer = GetCorrectAnswer();
            for (int i = 0; i < optionButtons.Length; i++)
            {
                optionButtons[i].interactable = false;
                if (_currentQuestion.options[i] == correctAnswer)
                    optionImages[i].color = _correctColor;
                else if (i == index && !correct)
                    optionImages[i].color = _wrongColor;
            }

            feedbackPanel.SetActive(true);
            feedbackText.text = correct ? "Correct!" : $"Answer: {correctAnswer}";

            _logic.AdvanceQuestion();
            Invoke(nameof(ShowNextQuestion), feedbackDelay);
        }

        private string GetCorrectAnswer()
        {
            return GameManager.Instance.QuizDirection switch
            {
                0 => _currentQuestion.correctEntry.chinese,
                1 => _currentQuestion.correctEntry.word,
                2 => _currentQuestion.correctEntry.word,
                _ => _currentQuestion.correctEntry.chinese
            };
        }
    }
}
```

**Step 2: Set up Quiz UI in Unity Editor (GamePlay scene)**

1. Open `GamePlay.unity` scene
2. Create Canvas (UI → Canvas, set to Scale With Screen Size, reference 1080x1920)
3. Add child elements:
   - **QuestionPanel** (top area): TextMeshPro text for the question word (font size 60+)
   - **ProgressText** (top-right): "1/10" counter
   - **ComboText** (top-left): combo display
   - **OptionButton_0 through OptionButton_3**: 4 large buttons (each ~900x120), stacked vertically in center. Each button has a child TextMeshProUGUI.
   - **FeedbackPanel**: overlay panel with TextMeshPro for "Correct!" / "Answer: ..."
4. Attach `QuizMode.cs` to a "QuizController" GameObject
5. Wire all UI references in the Inspector

**Step 3: Commit**

```bash
git add Assets/Scripts/GameModes/QuizMode.cs
git commit -m "feat: add QuizMode MonoBehaviour with UI feedback"
```

---

## Phase 6: Main Menu UI

### Task 10: Main Menu Screen

**Files:**
- Create: `Assets/Scripts/UI/MainMenuUI.cs`

**Step 1: Implement MainMenuUI**

`Assets/Scripts/UI/MainMenuUI.cs`:
```csharp
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using VocabularyGame.Core;

namespace VocabularyGame.UI
{
    public class MainMenuUI : MonoBehaviour
    {
        [Header("Buttons")]
        [SerializeField] private Button playButton;
        [SerializeField] private Button dailyChallengeButton;
        [SerializeField] private Button progressButton;
        [SerializeField] private Button achievementsButton;
        [SerializeField] private Button settingsButton;

        [Header("Info Display")]
        [SerializeField] private TextMeshProUGUI levelText;
        [SerializeField] private TextMeshProUGUI xpText;
        [SerializeField] private Slider xpBar;

        private void Start()
        {
            playButton.onClick.AddListener(OnPlayClicked);
            dailyChallengeButton.onClick.AddListener(OnDailyChallengeClicked);
            progressButton.onClick.AddListener(OnProgressClicked);
            achievementsButton.onClick.AddListener(OnAchievementsClicked);
            settingsButton.onClick.AddListener(OnSettingsClicked);

            UpdateDisplay();
        }

        private void UpdateDisplay()
        {
            var gm = GameManager.Instance;
            if (gm == null) return;

            var progress = gm.Progress;
            levelText.text = $"Lv. {progress.playerLevel}";
            xpText.text = $"{progress.totalXP} XP";
            xpBar.value = Progress.XPSystem.GetLevelProgress(progress.totalXP);
        }

        private void OnPlayClicked()
        {
            // Navigate to level select (can be a panel in same scene)
            // For simplicity, show level select panel
            GameManager.Instance.LoadScene("LevelSelect");
        }

        private void OnDailyChallengeClicked()
        {
            // TODO: Phase 7
        }

        private void OnProgressClicked()
        {
            // TODO: Phase 6
        }

        private void OnAchievementsClicked()
        {
            // TODO: Phase 6
        }

        private void OnSettingsClicked()
        {
            // TODO: Phase 8
        }
    }
}
```

**Step 2: Set up Main Menu UI in Unity Editor (MainMenu scene)**

1. Open `MainMenu.unity`
2. Add Canvas (Scale With Screen Size, 1080x1920)
3. Add elements:
   - **Title**: TextMeshPro "Vocabulary Game" (centered top, font size 72)
   - **PlayerInfo Panel** (below title): Level text, XP text, XP progress bar
   - **PlayButton**: Large button "Play" (centered)
   - **DailyChallengeButton**: "Daily Challenge"
   - **ProgressButton**: "Progress"
   - **AchievementsButton**: "Achievements"
   - **SettingsButton**: gear icon (top-right)
4. Attach `MainMenuUI.cs` → wire references

**Step 3: Commit**

```bash
git add Assets/Scripts/UI/MainMenuUI.cs
git commit -m "feat: add MainMenuUI with navigation"
```

---

### Task 11: Level Select and Mode Select UI

**Files:**
- Create: `Assets/Scripts/UI/LevelSelectUI.cs`
- Create: `Assets/Scripts/UI/ModeSelectUI.cs`

**Step 1: Implement LevelSelectUI**

`Assets/Scripts/UI/LevelSelectUI.cs`:
```csharp
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using VocabularyGame.Core;

namespace VocabularyGame.UI
{
    public class LevelSelectUI : MonoBehaviour
    {
        [SerializeField] private Button elementaryButton;
        [SerializeField] private Button juniorButton;
        [SerializeField] private Button seniorButton;
        [SerializeField] private Button backButton;
        [SerializeField] private TextMeshProUGUI elementaryProgress;
        [SerializeField] private TextMeshProUGUI juniorProgress;
        [SerializeField] private TextMeshProUGUI seniorProgress;

        private void Start()
        {
            elementaryButton.onClick.AddListener(() => SelectLevel(WordLevel.Elementary));
            juniorButton.onClick.AddListener(() => SelectLevel(WordLevel.Junior));
            seniorButton.onClick.AddListener(() => SelectLevel(WordLevel.Senior));
            backButton.onClick.AddListener(() => GameManager.Instance.GoToMainMenu());
        }

        private void SelectLevel(WordLevel level)
        {
            GameManager.Instance.SelectedLevel = level;
            GameManager.Instance.LoadScene("ModeSelect");
        }
    }
}
```

**Step 2: Implement ModeSelectUI**

`Assets/Scripts/UI/ModeSelectUI.cs`:
```csharp
using UnityEngine;
using UnityEngine.UI;
using VocabularyGame.Core;

namespace VocabularyGame.UI
{
    public class ModeSelectUI : MonoBehaviour
    {
        [SerializeField] private Button quizButton;
        [SerializeField] private Button matchingButton;
        [SerializeField] private Button spellingButton;
        [SerializeField] private Button pictureButton;
        [SerializeField] private Button flashcardButton;
        [SerializeField] private Button backButton;

        private void Start()
        {
            quizButton.onClick.AddListener(() => SelectMode(GameMode.Quiz));
            matchingButton.onClick.AddListener(() => SelectMode(GameMode.Matching));
            spellingButton.onClick.AddListener(() => SelectMode(GameMode.Spelling));
            pictureButton.onClick.AddListener(() => SelectMode(GameMode.Picture));
            flashcardButton.onClick.AddListener(() => SelectMode(GameMode.Flashcard));
            backButton.onClick.AddListener(() => GameManager.Instance.LoadScene("LevelSelect"));

            // Disable picture mode if no imageable words for this level
            var imageableWords = GameManager.Instance.GetImageableWords();
            pictureButton.interactable = imageableWords.Count >= 4;
        }

        private void SelectMode(GameMode mode)
        {
            GameManager.Instance.SelectedMode = mode;
            GameManager.Instance.StartGame();
        }
    }
}
```

**Step 3: Create LevelSelect and ModeSelect scenes in Unity Editor**

- Create `Assets/Scenes/LevelSelect.unity` and `Assets/Scenes/ModeSelect.unity`
- Add them to Build Settings
- Set up Canvas UI with buttons for each scene
- Wire references

**Step 4: Commit**

```bash
git add Assets/Scripts/UI/LevelSelectUI.cs Assets/Scripts/UI/ModeSelectUI.cs
git commit -m "feat: add level select and mode select UI screens"
```

---

### Task 12: Results Screen

**Files:**
- Create: `Assets/Scripts/UI/ResultsUI.cs`

**Step 1: Implement ResultsUI**

`Assets/Scripts/UI/ResultsUI.cs`:
```csharp
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using VocabularyGame.Core;
using VocabularyGame.Progress;

namespace VocabularyGame.UI
{
    public class ResultsUI : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI scoreText;
        [SerializeField] private TextMeshProUGUI accuracyText;
        [SerializeField] private TextMeshProUGUI xpEarnedText;
        [SerializeField] private TextMeshProUGUI comboText;
        [SerializeField] private Button playAgainButton;
        [SerializeField] private Button mainMenuButton;

        // These values should be set by the game mode before loading this scene
        public static int LastCorrectCount;
        public static int LastTotalQuestions;
        public static int LastXPEarned;
        public static int LastMaxCombo;

        private void Start()
        {
            scoreText.text = $"{LastCorrectCount} / {LastTotalQuestions}";

            float accuracy = LastTotalQuestions > 0
                ? (float)LastCorrectCount / LastTotalQuestions * 100f
                : 0;
            accuracyText.text = $"{accuracy:F0}%";

            xpEarnedText.text = $"+{LastXPEarned} XP";
            comboText.text = $"Max Combo: {LastMaxCombo}";

            playAgainButton.onClick.AddListener(() => GameManager.Instance.StartGame());
            mainMenuButton.onClick.AddListener(() => GameManager.Instance.GoToMainMenu());

            // Save progress
            GameManager.Instance.SaveProgress();
        }
    }
}
```

**Step 2: Set up Results scene in Unity Editor**

1. Open `Results.unity`
2. Canvas with score display, accuracy, XP earned, max combo
3. Two buttons: "Play Again" and "Main Menu"
4. Wire references

**Step 3: Commit**

```bash
git add Assets/Scripts/UI/ResultsUI.cs
git commit -m "feat: add results screen with score display"
```

---

## Phase 7: Remaining Game Modes

### Task 13: Matching Mode Logic + UI

**Files:**
- Create: `Assets/Scripts/GameModes/MatchingLogic.cs`
- Create: `Assets/Scripts/GameModes/MatchingMode.cs`
- Test: `Assets/Tests/EditMode/MatchingLogicTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/MatchingLogicTests.cs`:
```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Core;
using VocabularyGame.GameModes;

namespace VocabularyGame.Tests
{
    public class MatchingLogicTests
    {
        private List<VocabularyEntry> _testWords;

        [SetUp]
        public void Setup()
        {
            _testWords = new List<VocabularyEntry>
            {
                new() { word = "apple", chinese = "蘋果" },
                new() { word = "dog", chinese = "狗" },
                new() { word = "cat", chinese = "貓" },
                new() { word = "book", chinese = "書" },
                new() { word = "house", chinese = "房子" },
                new() { word = "car", chinese = "車" },
            };
        }

        [Test]
        public void GenerateBoard_Creates12Cards_For6Pairs()
        {
            var logic = new MatchingLogic(_testWords, pairCount: 6);
            var cards = logic.GetCards();
            Assert.AreEqual(12, cards.Count);
        }

        [Test]
        public void Cards_HaveMatchingPairs()
        {
            var logic = new MatchingLogic(_testWords, pairCount: 6);
            var cards = logic.GetCards();

            // Every English card should have a matching Chinese card
            foreach (var card in cards)
            {
                if (card.isEnglish)
                {
                    bool hasMatch = cards.Exists(c => !c.isEnglish && c.pairId == card.pairId);
                    Assert.IsTrue(hasMatch, $"No Chinese match for {card.text}");
                }
            }
        }

        [Test]
        public void FlipCard_ReturnsCard()
        {
            var logic = new MatchingLogic(_testWords, pairCount: 6);
            var cards = logic.GetCards();

            var result = logic.FlipCard(0);
            Assert.IsNotNull(result);
            Assert.IsTrue(result.isFlipped);
        }

        [Test]
        public void FlipTwoMatching_ReturnsMatch()
        {
            var logic = new MatchingLogic(_testWords, pairCount: 6);
            var cards = logic.GetCards();

            // Find a matching pair
            int first = -1, second = -1;
            for (int i = 0; i < cards.Count; i++)
            {
                for (int j = i + 1; j < cards.Count; j++)
                {
                    if (cards[i].pairId == cards[j].pairId)
                    {
                        first = i;
                        second = j;
                        break;
                    }
                }
                if (first >= 0) break;
            }

            logic.FlipCard(first);
            var matchResult = logic.FlipCard(second);
            Assert.IsTrue(logic.LastFlipWasMatch);
        }

        [Test]
        public void AllPairsMatched_GameComplete()
        {
            var logic = new MatchingLogic(_testWords, pairCount: 2);
            var cards = logic.GetCards();
            Assert.IsFalse(logic.IsComplete);

            // Match all pairs
            for (int i = 0; i < cards.Count; i++)
            {
                for (int j = i + 1; j < cards.Count; j++)
                {
                    if (cards[i].pairId == cards[j].pairId && !cards[i].isMatched)
                    {
                        logic.FlipCard(i);
                        logic.FlipCard(j);
                    }
                }
            }

            Assert.IsTrue(logic.IsComplete);
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement MatchingLogic**

`Assets/Scripts/GameModes/MatchingLogic.cs`:
```csharp
using System.Collections.Generic;
using System.Linq;
using VocabularyGame.Core;

namespace VocabularyGame.GameModes
{
    public class MatchCard
    {
        public int index;
        public int pairId;
        public string text;
        public bool isEnglish;
        public bool isFlipped;
        public bool isMatched;
        public VocabularyEntry entry;
    }

    public class MatchingLogic
    {
        private readonly List<MatchCard> _cards;
        private int _firstFlippedIndex = -1;
        public bool LastFlipWasMatch { get; private set; }
        public int FlipCount { get; private set; }
        public int MatchedPairs { get; private set; }
        public int TotalPairs { get; }
        public bool IsComplete => MatchedPairs >= TotalPairs;

        public MatchingLogic(List<VocabularyEntry> wordPool, int pairCount = 6)
        {
            TotalPairs = System.Math.Min(pairCount, wordPool.Count);
            var rng = new System.Random();
            var selected = wordPool.OrderBy(_ => rng.Next()).Take(TotalPairs).ToList();

            _cards = new List<MatchCard>();
            for (int i = 0; i < selected.Count; i++)
            {
                _cards.Add(new MatchCard
                {
                    pairId = i, text = selected[i].word,
                    isEnglish = true, entry = selected[i]
                });
                _cards.Add(new MatchCard
                {
                    pairId = i, text = selected[i].chinese,
                    isEnglish = false, entry = selected[i]
                });
            }

            // Shuffle
            _cards = _cards.OrderBy(_ => rng.Next()).ToList();
            for (int i = 0; i < _cards.Count; i++)
                _cards[i].index = i;
        }

        public List<MatchCard> GetCards() => _cards;

        public MatchCard FlipCard(int index)
        {
            var card = _cards[index];
            if (card.isMatched || card.isFlipped) return card;

            card.isFlipped = true;
            FlipCount++;
            LastFlipWasMatch = false;

            if (_firstFlippedIndex < 0)
            {
                _firstFlippedIndex = index;
            }
            else
            {
                var firstCard = _cards[_firstFlippedIndex];
                if (firstCard.pairId == card.pairId)
                {
                    firstCard.isMatched = true;
                    card.isMatched = true;
                    MatchedPairs++;
                    LastFlipWasMatch = true;
                }
                else
                {
                    firstCard.isFlipped = false;
                    card.isFlipped = false;
                }
                _firstFlippedIndex = -1;
            }

            return card;
        }

        public void ResetUnmatched()
        {
            foreach (var card in _cards)
            {
                if (!card.isMatched) card.isFlipped = false;
            }
            _firstFlippedIndex = -1;
        }
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Implement MatchingMode MonoBehaviour** (similar pattern to QuizMode — creates a grid of card buttons, handles flip animations via DOTween or coroutines)

`Assets/Scripts/GameModes/MatchingMode.cs` — follow same pattern as QuizMode: SerializeField references, Start() initializes logic, button click handlers call FlipCard.

**Step 6: Commit**

```bash
git add Assets/Scripts/GameModes/MatchingLogic.cs Assets/Scripts/GameModes/MatchingMode.cs \
      Assets/Tests/EditMode/MatchingLogicTests.cs
git commit -m "feat: add matching mode with card flip logic"
```

---

### Task 14: Spelling Mode Logic + UI

**Files:**
- Create: `Assets/Scripts/GameModes/SpellingLogic.cs`
- Create: `Assets/Scripts/GameModes/SpellingMode.cs`
- Test: `Assets/Tests/EditMode/SpellingLogicTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/SpellingLogicTests.cs`:
```csharp
using NUnit.Framework;
using VocabularyGame.GameModes;

namespace VocabularyGame.Tests
{
    public class SpellingLogicTests
    {
        [Test]
        public void ScrambleLetters_ContainsSameLetters()
        {
            var scrambled = SpellingLogic.ScrambleWord("apple");
            var sorted1 = new string(new char[] { 'a', 'e', 'l', 'p', 'p' });
            var sorted2 = new string(scrambled.OrderBy(c => c).ToArray());
            Assert.AreEqual(sorted1, sorted2);
        }

        [Test]
        public void CheckSpelling_Correct()
        {
            Assert.IsTrue(SpellingLogic.CheckSpelling("apple", "apple"));
        }

        [Test]
        public void CheckSpelling_CaseInsensitive()
        {
            Assert.IsTrue(SpellingLogic.CheckSpelling("apple", "Apple"));
        }

        [Test]
        public void CheckSpelling_Wrong()
        {
            Assert.IsFalse(SpellingLogic.CheckSpelling("apple", "aple"));
        }

        [Test]
        public void GetHint_ReturnsFirstLetter()
        {
            string hint = SpellingLogic.GetHint("apple", 1);
            Assert.AreEqual("a", hint);
        }

        [Test]
        public void GetHint_ReturnsTwoLetters()
        {
            string hint = SpellingLogic.GetHint("apple", 2);
            Assert.AreEqual("ap", hint);
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement SpellingLogic**

`Assets/Scripts/GameModes/SpellingLogic.cs`:
```csharp
using System.Linq;

namespace VocabularyGame.GameModes
{
    public static class SpellingLogic
    {
        public static char[] ScrambleWord(string word)
        {
            var rng = new System.Random();
            return word.ToLower().ToCharArray().OrderBy(_ => rng.Next()).ToArray();
        }

        public static bool CheckSpelling(string expected, string attempt)
        {
            return string.Equals(expected.Trim(), attempt.Trim(),
                System.StringComparison.OrdinalIgnoreCase);
        }

        public static string GetHint(string word, int revealCount)
        {
            int count = System.Math.Min(revealCount, word.Length);
            return word.Substring(0, count).ToLower();
        }
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Implement SpellingMode MonoBehaviour** — Shows Chinese + definition at top, scrambled letter tiles below. Player taps tiles to build the word. Submit button to check. Hint button reveals letters.

**Step 6: Commit**

```bash
git add Assets/Scripts/GameModes/SpellingLogic.cs Assets/Scripts/GameModes/SpellingMode.cs \
      Assets/Tests/EditMode/SpellingLogicTests.cs
git commit -m "feat: add spelling mode with letter scramble and hints"
```

---

### Task 15: Flashcard Mode with Spaced Repetition

**Files:**
- Create: `Assets/Scripts/GameModes/FlashcardLogic.cs`
- Create: `Assets/Scripts/GameModes/FlashcardMode.cs`
- Test: `Assets/Tests/EditMode/FlashcardLogicTests.cs`

**Step 1: Write failing test**

`Assets/Tests/EditMode/FlashcardLogicTests.cs`:
```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Core;
using VocabularyGame.GameModes;

namespace VocabularyGame.Tests
{
    public class FlashcardLogicTests
    {
        [Test]
        public void GetNextReviewWord_PrioritizesLowMastery()
        {
            var words = new List<VocabularyEntry>
            {
                new() { word = "easy", chinese = "簡單" },
                new() { word = "hard", chinese = "困難" },
            };
            var mastery = new Dictionary<string, int>
            {
                { "easy", 4 },
                { "hard", 1 }
            };

            var logic = new FlashcardLogic(words, mastery);
            var next = logic.GetNextCard();
            Assert.AreEqual("hard", next.word);
        }

        [Test]
        public void MarkKnown_MovesToNextCard()
        {
            var words = new List<VocabularyEntry>
            {
                new() { word = "a", chinese = "1" },
                new() { word = "b", chinese = "2" },
            };
            var logic = new FlashcardLogic(words, new Dictionary<string, int>());

            var first = logic.GetNextCard();
            logic.MarkKnown();
            var second = logic.GetNextCard();
            Assert.AreNotEqual(first.word, second.word);
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement FlashcardLogic**

`Assets/Scripts/GameModes/FlashcardLogic.cs`:
```csharp
using System.Collections.Generic;
using System.Linq;
using VocabularyGame.Core;

namespace VocabularyGame.GameModes
{
    public class FlashcardLogic
    {
        private readonly List<VocabularyEntry> _queue;
        private int _currentIndex;

        public FlashcardLogic(List<VocabularyEntry> words, Dictionary<string, int> mastery)
        {
            // Sort by mastery ascending (review weakest first), then shuffle within same mastery
            var rng = new System.Random();
            _queue = words
                .OrderBy(w => mastery.TryGetValue(w.word, out int m) ? m : 0)
                .ThenBy(_ => rng.Next())
                .ToList();
            _currentIndex = 0;
        }

        public VocabularyEntry GetNextCard()
        {
            if (_currentIndex >= _queue.Count) return null;
            return _queue[_currentIndex];
        }

        public void MarkKnown()
        {
            _currentIndex++;
        }

        public void MarkUnknown()
        {
            // Move current card to later in queue
            if (_currentIndex < _queue.Count)
            {
                var card = _queue[_currentIndex];
                _queue.RemoveAt(_currentIndex);
                int insertAt = System.Math.Min(_currentIndex + 5, _queue.Count);
                _queue.Insert(insertAt, card);
            }
        }

        public int RemainingCards => _queue.Count - _currentIndex;
        public bool IsComplete => _currentIndex >= _queue.Count;
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Implement FlashcardMode MonoBehaviour** — Card with swipe gestures (left=unknown, right=known), tap to flip.

**Step 6: Commit**

```bash
git add Assets/Scripts/GameModes/FlashcardLogic.cs Assets/Scripts/GameModes/FlashcardMode.cs \
      Assets/Tests/EditMode/FlashcardLogicTests.cs
git commit -m "feat: add flashcard mode with spaced repetition"
```

---

### Task 16: Picture Mode

**Files:**
- Create: `Assets/Scripts/GameModes/PictureMode.cs`

**Step 1: Implement PictureMode**

This mode reuses `QuizLogic` and `SpellingLogic` but filters for imageable words only and displays an image instead of text as the prompt. The MonoBehaviour loads the sprite from `Resources/Images/{category}/{word}.png`.

```csharp
// Key difference from QuizMode:
// - Filters words: GameManager.Instance.GetImageableWords()
// - Shows Image component instead of text prompt
// - Loads sprite: Resources.Load<Sprite>($"Images/{entry.type}/{entry.word}")
```

**Step 2: Prepare placeholder images**

- Create folders under `Assets/Resources/Images/` for each category
- Add at least 5-10 test images per category to validate the pipeline
- Images: 256x256 PNG, import as Sprite (2D and UI) in Unity

**Step 3: Commit**

```bash
git add Assets/Scripts/GameModes/PictureMode.cs
git commit -m "feat: add picture mode for imageable vocabulary"
```

---

## Phase 8: Achievement System

### Task 17: Achievement Definitions and Checker

**Files:**
- Create: `Assets/Scripts/Progress/AchievementSystem.cs`
- Test: `Assets/Tests/EditMode/AchievementSystemTests.cs`

**Step 1: Write the failing test**

`Assets/Tests/EditMode/AchievementSystemTests.cs`:
```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Progress;

namespace VocabularyGame.Tests
{
    public class AchievementSystemTests
    {
        [Test]
        public void FirstStep_UnlocksWhenOneMastered()
        {
            var progress = new PlayerProgress();
            progress.SetMastery("apple", 1);

            var unlocked = AchievementSystem.CheckNewAchievements(progress);
            Assert.Contains("first_step", unlocked);
        }

        [Test]
        public void WordCollector100_NotUnlockedWith50()
        {
            var progress = new PlayerProgress();
            for (int i = 0; i < 50; i++)
                progress.SetMastery($"word_{i}", 5);

            var unlocked = AchievementSystem.CheckNewAchievements(progress);
            Assert.IsFalse(unlocked.Contains("word_collector_100"));
        }

        [Test]
        public void DailyStreak7_UnlocksAtStreak7()
        {
            var progress = new PlayerProgress { dailyStreak = 7 };

            var unlocked = AchievementSystem.CheckNewAchievements(progress);
            Assert.Contains("daily_streak_7", unlocked);
        }

        [Test]
        public void AlreadyUnlocked_NotReturned()
        {
            var progress = new PlayerProgress();
            progress.SetMastery("apple", 1);
            progress.UnlockAchievement("first_step");

            var unlocked = AchievementSystem.CheckNewAchievements(progress);
            Assert.IsFalse(unlocked.Contains("first_step"));
        }
    }
}
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement AchievementSystem**

`Assets/Scripts/Progress/AchievementSystem.cs`:
```csharp
using System.Collections.Generic;
using System.Linq;

namespace VocabularyGame.Progress
{
    public static class AchievementSystem
    {
        public struct AchievementDef
        {
            public string id;
            public string name;
            public string description;
        }

        public static readonly AchievementDef[] Definitions = new[]
        {
            new AchievementDef { id = "first_step", name = "First Step", description = "Learn your first word" },
            new AchievementDef { id = "word_collector_100", name = "Word Collector (100)", description = "Master 100 words" },
            new AchievementDef { id = "word_collector_500", name = "Word Collector (500)", description = "Master 500 words" },
            new AchievementDef { id = "word_collector_1000", name = "Word Collector (1000)", description = "Master 1000 words" },
            new AchievementDef { id = "daily_streak_7", name = "Daily Streak (7)", description = "Play 7 days in a row" },
            new AchievementDef { id = "daily_streak_30", name = "Daily Streak (30)", description = "Play 30 days in a row" },
        };

        public static List<string> CheckNewAchievements(PlayerProgress progress)
        {
            var newlyUnlocked = new List<string>();

            int masteredCount = 0;
            int learnedCount = 0;
            for (int i = 0; i < progress.masteryKeys.Count && i < progress.masteryValues.Count; i++)
            {
                if (progress.masteryValues[i] >= 5) masteredCount++;
                if (progress.masteryValues[i] >= 1) learnedCount++;
            }
            // Also check runtime dict
            if (learnedCount == 0)
            {
                // Rebuild from GetMastery calls isn't possible without keys,
                // so we rely on the synced lists. Check if any word has mastery >= 1.
                // This is handled by the list counts above.
            }

            Check("first_step", learnedCount >= 1, progress, newlyUnlocked);
            Check("word_collector_100", masteredCount >= 100, progress, newlyUnlocked);
            Check("word_collector_500", masteredCount >= 500, progress, newlyUnlocked);
            Check("word_collector_1000", masteredCount >= 1000, progress, newlyUnlocked);
            Check("daily_streak_7", progress.dailyStreak >= 7, progress, newlyUnlocked);
            Check("daily_streak_30", progress.dailyStreak >= 30, progress, newlyUnlocked);

            return newlyUnlocked;
        }

        private static void Check(string id, bool condition, PlayerProgress progress, List<string> list)
        {
            if (condition && !progress.IsAchievementUnlocked(id))
            {
                progress.UnlockAchievement(id);
                list.Add(id);
            }
        }
    }
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add Assets/Scripts/Progress/AchievementSystem.cs Assets/Tests/EditMode/AchievementSystemTests.cs
git commit -m "feat: add achievement system with unlock checking"
```

---

## Phase 9: Daily Challenge

### Task 18: Daily Challenge Logic

**Files:**
- Create: `Assets/Scripts/Progress/DailyChallenge.cs`
- Test: `Assets/Tests/EditMode/DailyChallengeTests.cs`

**Step 1: Write failing test**

```csharp
using NUnit.Framework;
using System.Collections.Generic;
using VocabularyGame.Core;
using VocabularyGame.Progress;

namespace VocabularyGame.Tests
{
    public class DailyChallengeTests
    {
        [Test]
        public void GenerateChallenge_Returns15Words()
        {
            var words = CreateTestWords(100);
            var progress = new PlayerProgress();
            var challenge = DailyChallenge.Generate(words, progress);
            Assert.AreEqual(15, challenge.Count);
        }

        [Test]
        public void GenerateChallenge_Includes5NewWords()
        {
            var words = CreateTestWords(100);
            var progress = new PlayerProgress();
            // Mark 50 words as seen
            for (int i = 0; i < 50; i++)
                progress.SetMastery($"word_{i}", 2);

            var challenge = DailyChallenge.Generate(words, progress);
            int newCount = 0;
            foreach (var w in challenge)
                if (progress.GetMastery(w.word) == 0) newCount++;
            Assert.GreaterOrEqual(newCount, 5);
        }

        private List<VocabularyEntry> CreateTestWords(int count)
        {
            var list = new List<VocabularyEntry>();
            for (int i = 0; i < count; i++)
                list.Add(new VocabularyEntry
                {
                    word = $"word_{i}", chinese = $"字_{i}",
                    type = "Test", definition = $"def {i}",
                    level = WordLevel.Elementary
                });
            return list;
        }
    }
}
```

**Step 2: Implement DailyChallenge**

`Assets/Scripts/Progress/DailyChallenge.cs`:
```csharp
using System.Collections.Generic;
using System.Linq;
using VocabularyGame.Core;

namespace VocabularyGame.Progress
{
    public static class DailyChallenge
    {
        private const int ReviewCount = 10;
        private const int NewCount = 5;

        public static List<VocabularyEntry> Generate(
            List<VocabularyEntry> allWords, PlayerProgress progress)
        {
            var rng = new System.Random();
            var result = new List<VocabularyEntry>();

            // 10 review words (mastery 1-4, prioritize lowest)
            var reviewCandidates = allWords
                .Where(w => { int m = progress.GetMastery(w.word); return m >= 1 && m < 5; })
                .OrderBy(w => progress.GetMastery(w.word))
                .ThenBy(_ => rng.Next())
                .Take(ReviewCount)
                .ToList();
            result.AddRange(reviewCandidates);

            // 5 new words (mastery 0)
            var newCandidates = allWords
                .Where(w => progress.GetMastery(w.word) == 0)
                .OrderBy(_ => rng.Next())
                .Take(NewCount)
                .ToList();
            result.AddRange(newCandidates);

            // If not enough review words, fill with more new words
            while (result.Count < ReviewCount + NewCount)
            {
                var extra = allWords
                    .Where(w => !result.Contains(w))
                    .OrderBy(_ => rng.Next())
                    .FirstOrDefault();
                if (extra == null) break;
                result.Add(extra);
            }

            return result.OrderBy(_ => rng.Next()).ToList();
        }

        public static void UpdateStreak(PlayerProgress progress)
        {
            string today = System.DateTime.Now.ToString("yyyy-MM-dd");
            if (progress.lastPlayDate == today) return;

            string yesterday = System.DateTime.Now.AddDays(-1).ToString("yyyy-MM-dd");
            progress.dailyStreak = progress.lastPlayDate == yesterday
                ? progress.dailyStreak + 1
                : 1;
            progress.lastPlayDate = today;
        }
    }
}
```

**Step 3: Run test — expect PASS**

**Step 4: Commit**

```bash
git add Assets/Scripts/Progress/DailyChallenge.cs Assets/Tests/EditMode/DailyChallengeTests.cs
git commit -m "feat: add daily challenge with streak tracking"
```

---

## Phase 10: Polish and Cross-Platform

### Task 19: Object Pooling Utility

**Files:**
- Create: `Assets/Scripts/Utils/ObjectPool.cs`

Simple generic object pool for reusing UI elements (cards, buttons):

```csharp
using System.Collections.Generic;
using UnityEngine;

namespace VocabularyGame.Utils
{
    public class ObjectPool : MonoBehaviour
    {
        [SerializeField] private GameObject prefab;
        [SerializeField] private int initialSize = 10;
        [SerializeField] private Transform container;

        private readonly Queue<GameObject> _pool = new();

        private void Awake()
        {
            for (int i = 0; i < initialSize; i++)
                CreateNew();
        }

        private void CreateNew()
        {
            var obj = Instantiate(prefab, container);
            obj.SetActive(false);
            _pool.Enqueue(obj);
        }

        public GameObject Get()
        {
            if (_pool.Count == 0) CreateNew();
            var obj = _pool.Dequeue();
            obj.SetActive(true);
            return obj;
        }

        public void Return(GameObject obj)
        {
            obj.SetActive(false);
            _pool.Enqueue(obj);
        }

        public void ReturnAll()
        {
            foreach (Transform child in container)
            {
                if (child.gameObject.activeSelf)
                {
                    child.gameObject.SetActive(false);
                    _pool.Enqueue(child.gameObject);
                }
            }
        }
    }
}
```

**Commit:**
```bash
git add Assets/Scripts/Utils/ObjectPool.cs
git commit -m "feat: add generic ObjectPool for UI element reuse"
```

---

### Task 20: Settings System

**Files:**
- Create: `Assets/Scripts/UI/SettingsUI.cs`

Simple settings panel with toggles for sound, timer, quiz direction, font size. Saves to PlayerPrefs.

**Commit:**
```bash
git add Assets/Scripts/UI/SettingsUI.cs
git commit -m "feat: add settings UI with sound, timer, and direction toggles"
```

---

### Task 21: Cross-Platform Build Setup

**Step 1: Configure build settings in Unity Editor**

- File → Build Settings
- Add all scenes in order: MainMenu, LevelSelect, ModeSelect, GamePlay, Results
- Player Settings:
  - Company Name, Product Name, Version
  - Default orientation: Portrait (mobile) / Auto (desktop)
  - Minimum API level: Android 7.0+ / iOS 13+

**Step 2: Test WebGL build**

- Switch platform to WebGL
- Build and Run → verify in browser

**Step 3: Test Android build**

- Install Android SDK via Unity Hub
- Switch platform to Android
- Build APK → test on device or emulator

**Step 4: Commit final build configs**

```bash
git add ProjectSettings/
git commit -m "feat: configure cross-platform build settings"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | Task 1 | Data preparation (enhanced CSV) |
| 2 | Task 2 | Unity project setup |
| 3 | Tasks 3-6 | Core data system (model, loader, progress, XP) |
| 4 | Task 7 | GameManager singleton |
| 5 | Tasks 8-9 | Quiz mode (first playable) |
| 6 | Tasks 10-12 | Menu UI (main, level select, mode select, results) |
| 7 | Tasks 13-16 | Remaining game modes (matching, spelling, flashcard, picture) |
| 8 | Task 17 | Achievement system |
| 9 | Task 18 | Daily challenge |
| 10 | Tasks 19-21 | Polish (object pool, settings, cross-platform) |

**Total: 21 tasks, ~9 phases**

Each task follows TDD where applicable: write failing test → implement → verify pass → commit.
