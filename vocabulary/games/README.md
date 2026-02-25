# 🎮 小一英語遊戲學習系列 — Flutter Flame

> 適合對象：小一學生 (6-7 歲) ｜ 總單字數：1,200 個 ｜ 遊戲數：32 個
> 技術：Flutter + Flame Engine ｜ 平台：iOS / Android / Web

本系列將 1,200 個基礎英語單字融入**互動遊戲**中，讓孩子透過「玩遊戲」自然習得英文單字。
使用 Flutter Flame 遊戲引擎開發，支援跨平台，操作簡單直覺，適合小一學生觸控操作。

---

## 設計原則

1. **遊戲優先**：先好玩，再學習；每個遊戲可獨立玩 5-10 分鐘
2. **正向回饋**：答對得星星/金幣，答錯不扣分只鼓勵重試
3. **漸進難度**：每個遊戲分 3 關（Easy → Medium → Hard）
4. **視覺豐富**：大圖示、鮮豔色彩、可愛角色動畫
5. **聽覺輔助**：所有單字附帶語音，點擊即播放發音
6. **觸控操作**：拖拉、點擊、滑動為主，無需打字

## Flutter Flame 技術規格

| 項目 | 規格 |
|------|------|
| 框架 | Flutter 3.x + Flame 1.x |
| 渲染 | Flame GameWidget, SpriteComponent |
| 音效 | flame_audio (背景音樂 + 音效) |
| 動畫 | SpriteAnimation + Effects (ScaleEffect, MoveEffect) |
| 物理 | 簡易碰撞偵測 (HasCollisionDetection) |
| 狀態管理 | flame_bloc / Provider |
| 資料儲存 | SharedPreferences (進度) + SQLite (學習記錄) |
| 螢幕適配 | FixedResolutionViewport (1080x1920) |
| 素材格式 | PNG sprites + JSON atlas, MP3 音效 |

## 遊戲類型定義

本系列共使用 **8 種核心遊戲機制**，每個主題選用 2-3 種最適合的機制：

| 代號 | 遊戲機制 | 說明 | Flame 技術 |
|------|----------|------|------------|
| 🎯 TAP | 點擊選擇 | 聽音選圖 / 看圖選字 | TapCallbacks + SpriteComponent |
| 🧩 DRAG | 拖拉配對 | 拖動單字到對應圖片 | DragCallbacks + HasCollisionDetection |
| 🏃 RUNNER | 跑酷收集 | 角色跑步收集正確單字 | ParallaxComponent + SpriteAnimation |
| 💥 POP | 泡泡消除 | 戳破包含正確單字的泡泡 | CircleComponent + RemoveEffect |
| 🃏 MATCH | 記憶翻牌 | 翻牌配對英文與圖片 | FlipEffect + SpriteComponent |
| 🎪 CATCH | 接住落下 | 用籃子接住正確單字 | MoveEffect + CollisionCallbacks |
| 🏗️ BUILD | 拼圖組裝 | 拼出正確字母順序 | DragCallbacks + SnapEffect |
| 🎰 SPIN | 轉盤抽獎 | 轉盤停在單字上回答問題 | RotateEffect + TimerComponent |

---

## 目錄

### 第一類：生活基礎

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 01 | [01-family-and-people.md](01-family-and-people.md) | 家庭與人物 | 30 | 🧩 DRAG + 🃏 MATCH |
| 02 | [02-body-and-health.md](02-body-and-health.md) | 身體與健康 | 40 | 🎯 TAP + 🧩 DRAG |
| 03 | [03-food-and-drinks.md](03-food-and-drinks.md) | 食物與飲料 | 55 | 🎪 CATCH + 🏃 RUNNER |
| 04 | [04-animals.md](04-animals.md) | 動物 | 35 | 🃏 MATCH + 💥 POP |
| 05 | [05-colors-and-shapes.md](05-colors-and-shapes.md) | 顏色與形狀 | 26 | 🎯 TAP + 🏗️ BUILD |

### 第二類：日常生活

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 06 | [06-numbers-and-counting.md](06-numbers-and-counting.md) | 數字與計數 | 38 | 🎯 TAP + 💥 POP |
| 07 | [07-time-and-calendar.md](07-time-and-calendar.md) | 時間與日曆 | 56 | 🎰 SPIN + 🧩 DRAG |
| 08 | [08-clothes-and-accessories.md](08-clothes-and-accessories.md) | 衣服與配件 | 30 | 🧩 DRAG + 🏗️ BUILD |
| 09 | [09-house-and-home.md](09-house-and-home.md) | 家與居家 | 50 | 🧩 DRAG + 🎯 TAP |
| 10 | [10-school-and-education.md](10-school-and-education.md) | 學校與教育 | 50 | 🎪 CATCH + 🃏 MATCH |

### 第三類：外出探索

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 11 | [11-weather-and-nature.md](11-weather-and-nature.md) | 天氣與自然 | 50 | 🎪 CATCH + 🎯 TAP |
| 12 | [12-transportation-and-travel.md](12-transportation-and-travel.md) | 交通與旅行 | 35 | 🏃 RUNNER + 💥 POP |
| 13 | [13-feelings-and-emotions.md](13-feelings-and-emotions.md) | 感覺與情緒 | 30 | 🃏 MATCH + 🎯 TAP |
| 15 | [15-places-in-town.md](15-places-in-town.md) | 城鎮中的地方 | 30 | 🧩 DRAG + 🏃 RUNNER |
| 16 | [16-jobs-and-occupations.md](16-jobs-and-occupations.md) | 工作與職業 | 30 | 🎰 SPIN + 🃏 MATCH |

### 第四類：動詞遊戲（共 4 個）

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 14-1 | [14-common-verbs-1-daily.md](14-common-verbs-1-daily.md) | 日常動作動詞 | ~25 | 🏃 RUNNER + 🎯 TAP |
| 14-2 | [14-common-verbs-2-movement.md](14-common-verbs-2-movement.md) | 移動動詞 | ~25 | 🏃 RUNNER + 💥 POP |
| 14-3 | [14-common-verbs-3-communication.md](14-common-verbs-3-communication.md) | 溝通動詞 | ~25 | 🎯 TAP + 🎰 SPIN |
| 14-4 | [14-common-verbs-4-thinking.md](14-common-verbs-4-thinking.md) | 思考與感受動詞 | ~22 | 🃏 MATCH + 💥 POP |

### 第五類：興趣與社會

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 17 | [17-sports-and-hobbies.md](17-sports-and-hobbies.md) | 運動與嗜好 | 35 | 🏃 RUNNER + 🎪 CATCH |
| 18 | [18-technology-and-communication.md](18-technology-and-communication.md) | 科技與通訊 | 30 | 🎯 TAP + 🏗️ BUILD |
| 19 | [19-shopping-and-money.md](19-shopping-and-money.md) | 購物與金錢 | 25 | 🧩 DRAG + 🎰 SPIN |

### 第六類：形容詞遊戲（共 4 個）

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 20-1 | [20-adjectives-1-size-shape.md](20-adjectives-1-size-shape.md) | 形容詞：大小形狀 | ~20 | 🧩 DRAG + 🎯 TAP |
| 20-2 | [20-adjectives-2-feelings.md](20-adjectives-2-feelings.md) | 形容詞：感受 | ~20 | 🃏 MATCH + 💥 POP |
| 20-3 | [20-adjectives-3-quality.md](20-adjectives-3-quality.md) | 形容詞：品質特徵 | ~20 | 🎯 TAP + 🎪 CATCH |
| 20-4 | [20-adjectives-4-other.md](20-adjectives-4-other.md) | 形容詞：其他 | ~20 | 💥 POP + 🎰 SPIN |

### 第七類：進階遊戲

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 21 | [21-prepositions-and-directions.md](21-prepositions-and-directions.md) | 介系詞與方向 | 45 | 🧩 DRAG + 🏃 RUNNER |
| 22 | [22-common-nouns.md](22-common-nouns.md) | 常見名詞 | 70 | 🎪 CATCH + 🃏 MATCH |
| 23 | [23-social-words-and-phrases.md](23-social-words-and-phrases.md) | 社交用語 | 35 | 🎰 SPIN + 🎯 TAP |

### 第八類：補充遊戲（共 4 個）

| 編號 | 檔案 | 主題 | 單字數 | 核心遊戲機制 |
|------|------|------|--------|-------------|
| 24-1 | [24-bonus-1-connectors.md](24-bonus-1-connectors.md) | 連接詞與副詞 | ~42 | 🏗️ BUILD + 🎯 TAP |
| 24-2 | [24-bonus-2-more-verbs.md](24-bonus-2-more-verbs.md) | 更多動詞 | ~58 | 🏃 RUNNER + 🎪 CATCH |
| 24-3 | [24-bonus-3-more-nouns.md](24-bonus-3-more-nouns.md) | 更多名詞 | ~50 | 💥 POP + 🃏 MATCH |
| 24-4 | [24-bonus-4-more-adjectives.md](24-bonus-4-more-adjectives.md) | 更多形容詞 | ~50 | 🎯 TAP + 🧩 DRAG |

---

## 遊戲難度設計

| 難度 | 說明 | 單字數/輪 | 時間限制 | 干擾項 |
|------|------|-----------|----------|--------|
| ⭐ Easy | 看圖聽音選擇 | 4 個 | 無 | 2 個選項 |
| ⭐⭐ Medium | 聽音選字 | 6 個 | 15 秒/題 | 3 個選項 |
| ⭐⭐⭐ Hard | 拼字 + 聽力混合 | 8 個 | 10 秒/題 | 4 個選項 |

## 獎勵系統

| 獎勵 | 獲得方式 | Flame 實作 |
|------|----------|-----------|
| ⭐ 星星 | 每答對一題 +1 | ScaleEffect + ParticleComponent |
| 🪙 金幣 | 連續答對 3 題 +5 | MoveEffect 飛入錢包動畫 |
| 🏆 獎盃 | 通過一關 | OverlayRoute 顯示成就 |
| 🎁 角色解鎖 | 累計星星達標 | SharedPreferences 存進度 |
| 🌈 特效 | 全答對 | ParticleSystemComponent 煙火效果 |

---

## 建議遊玩順序

1. **入門**：動物 (04)、食物 (03)、顏色 (05) — 圖像辨識最直覺
2. **互動**：身體 (02)、衣服 (08)、感覺 (13) — 搭配動作互動
3. **場景**：居家 (09)、學校 (10)、交通 (12)、天氣 (11)
4. **動作**：動詞系列 (14-1~4) — 跑酷遊戲最適合
5. **進階**：其餘主題依興趣解鎖

---

## Flutter 專案結構（參考）

```
lib/
├── main.dart
├── app/
│   ├── game_app.dart           # FlameGame 主入口
│   └── router.dart             # 關卡路由
├── components/
│   ├── word_card.dart          # 單字卡片元件
│   ├── word_bubble.dart        # 泡泡元件
│   ├── player.dart             # 玩家角色
│   └── reward_particle.dart    # 獎勵粒子效果
├── games/
│   ├── tap_game.dart           # 🎯 點擊選擇
│   ├── drag_match_game.dart    # 🧩 拖拉配對
│   ├── runner_game.dart        # 🏃 跑酷收集
│   ├── pop_game.dart           # 💥 泡泡消除
│   ├── memory_match_game.dart  # 🃏 記憶翻牌
│   ├── catch_game.dart         # 🎪 接住落下
│   ├── build_game.dart         # 🏗️ 拼圖組裝
│   └── spin_game.dart          # 🎰 轉盤抽獎
├── data/
│   ├── word_repository.dart    # 單字資料管理
│   └── progress_store.dart     # 學習進度儲存
├── audio/
│   └── audio_manager.dart      # 音效與 TTS 管理
└── ui/
    ├── home_screen.dart        # 主選單
    ├── category_screen.dart    # 分類選擇
    └── result_screen.dart      # 結果畫面
```

---

## 資料來源

所有單字來自 [`1200-essential-english-words-with-chinese.md`](../1200-essential-english-words-with-chinese.md)
