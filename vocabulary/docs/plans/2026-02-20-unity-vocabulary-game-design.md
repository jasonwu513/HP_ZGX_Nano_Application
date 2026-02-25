# Unity Vocabulary Game - Design Document

> Date: 2026-02-20
> Status: Approved

---

## Overview

A cross-platform 2D card-based vocabulary learning game built with Unity. Supports 12,200 English words across three difficulty levels (Elementary 1,200 / Junior High 3,000 / Senior High 8,000) with multiple game modes, picture-word association for concrete nouns, and a full progression system.

## Target Audience

All age groups. Users select their difficulty level (Elementary / Junior High / Senior High), and the game adapts accordingly.

## Platform

Cross-platform: iOS, Android, Windows, Mac. Built with Unity Canvas UI for maximum compatibility.

---

## Architecture

### Project Structure

```
VocabularyGame/
├── Assets/
│   ├── Scripts/
│   │   ├── Core/                  # Core game systems
│   │   │   ├── GameManager.cs     # Global game state, scene transitions
│   │   │   ├── VocabularyData.cs  # Word data model (word, chinese, type, definition, hasImage)
│   │   │   └── DataLoader.cs     # CSV parser, loads vocabulary into memory
│   │   ├── GameModes/             # Game mode controllers
│   │   │   ├── QuizMode.cs       # Multiple choice quiz
│   │   │   ├── MatchingMode.cs   # Card matching game
│   │   │   ├── SpellingMode.cs   # Letter drag-and-drop spelling
│   │   │   ├── PictureMode.cs    # Picture-to-word guessing
│   │   │   └── FlashcardMode.cs  # Swipeable flashcards
│   │   ├── UI/                    # UI controllers
│   │   │   ├── MainMenuUI.cs
│   │   │   ├── LevelSelectUI.cs
│   │   │   ├── ModeSelectUI.cs
│   │   │   ├── TopicSelectUI.cs
│   │   │   ├── GameplayUI.cs
│   │   │   ├── ResultUI.cs
│   │   │   ├── ProgressUI.cs
│   │   │   └── SettingsUI.cs
│   │   └── Progress/              # Progression and achievements
│   │       ├── ProgressManager.cs     # Word mastery tracking
│   │       ├── AchievementSystem.cs   # Badge/achievement logic
│   │       ├── StatisticsTracker.cs   # Learning statistics
│   │       ├── XPSystem.cs            # Experience and leveling
│   │       └── DailyChallenge.cs      # Daily challenge generation
│   ├── Data/
│   │   └── vocabulary.csv         # All 12,200 words (copied from existing project)
│   ├── Images/
│   │   ├── Animals/               # Animal icons
│   │   ├── Food/                  # Food icons
│   │   ├── Body/                  # Body part icons
│   │   ├── Clothes/               # Clothing icons
│   │   ├── Transportation/        # Vehicle icons
│   │   ├── House/                 # Household item icons
│   │   ├── Jobs/                  # Occupation icons
│   │   └── ...                    # Other imageable categories
│   ├── Prefabs/
│   │   ├── WordCard.prefab        # Reusable word card
│   │   ├── QuizOption.prefab      # Quiz answer button
│   │   ├── LetterTile.prefab      # Draggable letter for spelling
│   │   ├── MatchCard.prefab       # Matching game card
│   │   └── AchievementBadge.prefab
│   ├── Scenes/
│   │   ├── MainMenu.unity
│   │   ├── GamePlay.unity
│   │   └── Results.unity
│   └── Resources/
│       ├── Fonts/                 # Noto Sans TC (Chinese + English)
│       └── Sprites/               # UI sprites (buttons, backgrounds, icons)
├── ProjectSettings/
└── Packages/
```

### Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| UI System | Unity Canvas UI | More beginner-friendly than UI Toolkit, more tutorials available |
| Data Format | CSV imported at runtime | Reuses existing vocabulary.csv directly |
| Data Storage | PlayerPrefs + JSON | Local storage, no server needed |
| Image Format | PNG 256x256, Sprite Atlas | Good balance of quality and file size |
| Object Management | Object Pooling | Reuse card/button objects to minimize memory allocation |

---

## Game Modes

### Mode 1: Quiz Mode (Four-Choice)

- Display an English word (or Chinese) at the top
- Four answer buttons below; one correct, three distractors
- Switchable directions: EN→CN / CN→EN / Definition→Word
- Optional timer: 10-second countdown per question
- Combo scoring for consecutive correct answers
- 10-20 questions per round

### Mode 2: Matching Mode (Card Flip)

- Grid of face-down cards (4x3 or 4x4)
- Flip two cards; English matches Chinese = pair removed
- Track flip count and time
- Higher difficulty = more cards on screen
- Uses Object Pooling for card instances

### Mode 3: Spelling Mode (Letter Drag)

- Show Chinese meaning and English definition
- Scrambled letter tiles displayed below
- Drag or tap letters to spell the correct word
- Hint button: reveals the first letter
- Scoring based on speed and hint usage

### Mode 4: Picture Mode (Picture-to-Word)

- **Only available for words with associated images** (~800-1,500 concrete nouns)
- Display an image; user guesses the word
- Two sub-modes:
  - Spell: drag letters to spell the word shown in the picture
  - Quiz: four-choice, pick the correct word for the picture
- Categories: Animals, Food, Body, Clothes, Transportation, House, Jobs, etc.

### Mode 5: Flashcard Mode (Spaced Repetition)

- Display English word on a card
- Tap to flip: reveals Chinese translation and definition
- Swipe left = "Don't know" (add to review queue, show again sooner)
- Swipe right = "Know it" (mark as learned, show again later)
- Spaced repetition scheduling (intervals: 1 day → 3 days → 7 days → 14 days → 30 days)

---

## Image Asset Strategy

### Hybrid Approach

Not all 12,200 words need images. Only concrete, visually representable nouns get images.

| Category | Imageable? | Example Words |
|----------|-----------|---------------|
| Animals | Yes | dog, cat, elephant |
| Food & Drinks | Yes | apple, rice, milk |
| Body & Health | Yes | hand, eye, heart |
| Clothes | Yes | shirt, hat, shoes |
| Transportation | Yes | car, bus, airplane |
| House & Home | Yes | bed, table, window |
| Jobs | Yes | doctor, teacher, farmer |
| Common Nouns | Partial | book, phone, clock |
| Verbs | No | run, think, become |
| Adjectives | No | happy, large, important |
| Abstract Nouns | No | freedom, idea, reason |

### Image Sources

- Free icon libraries: Flaticon, OpenClipart, Icons8 (check licenses)
- Consistent flat/outline style across all images
- Format: PNG, 256x256 pixels
- Packed into Unity Sprite Atlases for draw call optimization

### Estimated Image Count

- Elementary level: ~400-600 words imageable
- Junior High level: ~300-500 words imageable
- Senior High level: ~200-400 words imageable
- **Total: ~800-1,500 images**

---

## Progression System

### Word Mastery

Each word has a mastery level from 0 to 5:

| Level | Name | Description |
|-------|------|-------------|
| 0 | Unseen | Never encountered |
| 1 | Seen | Encountered but not tested |
| 2 | Recognized | Answered correctly once |
| 3 | Remembered | Answered correctly 3 times |
| 4 | Familiar | Answered correctly 5 times with <20% error rate |
| 5 | Mastered | Answered correctly 8+ times with <10% error rate |

- Correct answer: mastery +1 (up to 5)
- Incorrect answer: mastery -1 (down to minimum 1 if previously learned)

### XP and Leveling

- Correct answer: +10 XP base
- Combo bonus: +5 XP per consecutive correct (up to +50)
- Daily challenge completion: +100 XP
- Player levels 1-50, XP curve increases per level

### Achievement Badges

| Achievement | Condition |
|-------------|-----------|
| First Step | Learn your first word |
| Word Collector (100) | 100 words at mastery 5 |
| Word Collector (500) | 500 words at mastery 5 |
| Word Collector (1000) | 1000 words at mastery 5 |
| Perfect Round | Answer all questions correctly in one quiz round |
| Speed Demon | Complete a timed quiz with 100% accuracy |
| Daily Streak (7) | Use the app 7 days in a row |
| Daily Streak (30) | Use the app 30 days in a row |
| Spelling Bee | 20 consecutive correct in spelling mode |
| Picture Perfect | 50 correct in picture mode |
| Topic Master | Master all words in one topic |
| Level Complete | Master all words in one difficulty level |

### Daily Challenge

- 10 review words (from previously learned, prioritizing low mastery)
- 5 new words (from current difficulty level)
- Completion awards bonus XP
- Streak tracking for consecutive daily completions

### Progress Tracking

- Per-level completion percentage (Elementary / Junior High / Senior High)
- Per-topic progress within each level
- Overall mastery distribution chart
- Learning statistics: words learned per day, accuracy rate, time spent

---

## UI Flow

```
App Launch
  └── Main Menu
        ├── Play
        │     ├── Select Level (Elementary / Junior High / Senior High)
        │     ├── Select Mode (Quiz / Matching / Spelling / Picture / Flashcard)
        │     ├── Select Topic (All / specific topic)
        │     └── Gameplay → Results → Back to Main Menu
        ├── Daily Challenge
        │     └── 15-question mixed session → Results
        ├── Progress
        │     ├── Learning Statistics
        │     ├── Mastery Distribution
        │     └── Per-topic Breakdown
        ├── Achievements
        │     └── Badge gallery with unlock status
        └── Settings
              ├── Sound effects (on/off)
              ├── Timer (on/off)
              ├── Quiz direction (EN→CN / CN→EN / Definition→Word)
              └── Font size
```

### UI Style

- Clean, flat design with large readable text
- Color palette: soft blue, green, orange as primary colors; white backgrounds
- Large tap-friendly buttons (mobile-first)
- Correct answer: green animation + sound effect
- Wrong answer: red flash + show correct answer for 2 seconds
- Font: Noto Sans TC (supports Chinese + English)
- Responsive layout that adapts to phone, tablet, and desktop screens

---

## Data Model

### VocabularyEntry

```csharp
[System.Serializable]
public class VocabularyEntry
{
    public string word;          // English word
    public string chinese;       // Chinese translation
    public string type;          // Topic/category (e.g., "Animals")
    public string definition;    // English definition
    public string level;         // "elementary" / "junior" / "senior"
    public bool hasImage;        // Whether an image exists for this word
    public string imagePath;     // Path to image sprite (if hasImage)
}
```

### PlayerProgress (JSON serialized)

```csharp
[System.Serializable]
public class PlayerProgress
{
    public int playerLevel;
    public int totalXP;
    public int dailyStreak;
    public string lastPlayDate;
    public Dictionary<string, int> wordMastery;     // word -> mastery level (0-5)
    public Dictionary<string, bool> achievements;    // achievement_id -> unlocked
    public Dictionary<string, int> wordCorrectCount; // word -> times answered correctly
    public Dictionary<string, int> wordWrongCount;   // word -> times answered wrong
}
```

---

## Resource Estimates

| Asset | Estimated Size |
|-------|---------------|
| Vocabulary CSV data | ~1 MB |
| Font (Noto Sans TC) | ~5-15 MB |
| Word images (~1000 x 256x256 PNG) | ~20-40 MB |
| UI sprites (buttons, backgrounds, icons) | ~2-3 MB |
| Achievement badge icons (~15) | ~1 MB |
| Sound effects | ~2-5 MB |
| **Total build size** | **~30-65 MB** |

### Runtime Memory

- Only 10-20 words loaded per game round
- Object Pooling for card/button UI elements
- Sprite Atlas for batched draw calls
- Word mastery dictionary stays in memory (~200 KB for 12,200 entries)

---

## Development Phases (High Level)

1. **Phase 1 - Core Setup**: Unity project, data loading, basic UI navigation
2. **Phase 2 - Quiz Mode**: First playable game mode
3. **Phase 3 - Matching + Spelling Modes**: Two more modes
4. **Phase 4 - Picture Mode**: Image integration, picture-word gameplay
5. **Phase 5 - Flashcard Mode**: Spaced repetition
6. **Phase 6 - Progression System**: XP, mastery tracking, achievements
7. **Phase 7 - Daily Challenge**: Mixed-mode daily session
8. **Phase 8 - Polish**: Sound effects, animations, responsive layout
9. **Phase 9 - Cross-platform Build**: iOS, Android, Windows, Mac builds
