# 🎧 小一英語聽力故事學習系列

> 適合對象：小一學生 (6-7 歲) ｜ 總單字數：1,200 個 ｜ 故事數：32 篇
> 技術：ASR (Automatic Speech Recognition) + TTS (Text-to-Speech)

本系列將 1,200 個基礎英語單字融入**有聲故事**中，讓孩子透過「聽故事」自然習得英文單字。
每篇故事搭配 TTS 語音朗讀，孩子可反覆聆聽，從語境中理解單字意義。

---

## 設計原則

1. **聽覺優先**：每篇故事設計為 3-5 分鐘的語音內容，適合小一注意力長度
2. **重複曝光**：每個目標單字在故事中至少出現 3 次，加深記憶
3. **中英混合**：故事主體為中文，目標英文單字以英文呈現並由 TTS 朗讀
4. **情境自然**：單字融入生活化情境，不強制背誦
5. **互動提問**：每段故事後附帶簡單聽力問題，確認理解

## TTS 技術規格

| 項目 | 規格 |
|------|------|
| TTS 引擎 | Google Cloud TTS / Azure Cognitive Services |
| 英文語音 | en-US, 語速 0.8x（放慢適合兒童） |
| 中文語音 | zh-TW（繁體中文） |
| 輸出格式 | MP3 / OGG, 44.1kHz |
| 音檔結構 | 每篇故事一個完整音檔 + 分段音檔（逐段聆聽） |

## ASR 互動規格

| 項目 | 規格 |
|------|------|
| ASR 引擎 | Google Cloud Speech-to-Text / Azure Speech |
| 功能 | 孩子跟讀單字，系統辨識發音正確度 |
| 回饋 | 正確 → 鼓勵音效 + 星星；需改進 → 再聽一次示範 |
| 容錯率 | 設定為寬鬆模式（confidence threshold 0.6），鼓勵開口 |

## 故事結構模板

每篇故事 markdown 包含：

```
1. 故事資訊（主題、目標單字數、預估時長）
2. 目標單字列表（含中英文與發音標記）
3. 故事正文（分 3-4 段，每段 8-12 句）
4. TTS 標記（標注語言切換點、停頓點、語速調整）
5. 聽力小測驗（3-5 題選擇題，聽音辨字）
6. 跟讀練習（5-8 個核心單字，ASR 跟讀）
7. 親子延伸（建議家長與孩子的互動活動）
```

---

## 目錄

### 第一類：生活基礎

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 01 | [01-family-and-people.md](01-family-and-people.md) | 家庭與人物 | 30 | 《熱鬧的家庭野餐日》 |
| 02 | [02-body-and-health.md](02-body-and-health.md) | 身體與健康 | 40 | 《身體王國大冒險》 |
| 03 | [03-food-and-drinks.md](03-food-and-drinks.md) | 食物與飲料 | 55 | 《小小廚師的魔法廚房》 |
| 04 | [04-animals.md](04-animals.md) | 動物 | 35 | 《動物園的奇妙一天》 |
| 05 | [05-colors-and-shapes.md](05-colors-and-shapes.md) | 顏色與形狀 | 26 | 《彩虹村的形狀精靈》 |

### 第二類：日常生活

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 06 | [06-numbers-and-counting.md](06-numbers-and-counting.md) | 數字與計數 | 38 | 《數字精靈的寶藏地圖》 |
| 07 | [07-time-and-calendar.md](07-time-and-calendar.md) | 時間與日曆 | 56 | 《時鐘爺爺的一天》 |
| 08 | [08-clothes-and-accessories.md](08-clothes-and-accessories.md) | 衣服與配件 | 30 | 《魔法衣櫥大變身》 |
| 09 | [09-house-and-home.md](09-house-and-home.md) | 家與居家 | 50 | 《小熊搬新家》 |
| 10 | [10-school-and-education.md](10-school-and-education.md) | 學校與教育 | 50 | 《第一天上學記》 |

### 第三類：外出探索

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 11 | [11-weather-and-nature.md](11-weather-and-nature.md) | 天氣與自然 | 50 | 《天氣仙子的四季旅行》 |
| 12 | [12-transportation-and-travel.md](12-transportation-and-travel.md) | 交通與旅行 | 35 | 《環遊世界交通工具》 |
| 13 | [13-feelings-and-emotions.md](13-feelings-and-emotions.md) | 感覺與情緒 | 30 | 《心情小怪獸》 |
| 15 | [15-places-in-town.md](15-places-in-town.md) | 城鎮中的地方 | 30 | 《小鎮探險地圖》 |
| 16 | [16-jobs-and-occupations.md](16-jobs-and-occupations.md) | 工作與職業 | 30 | 《長大後我想當⋯》 |

### 第四類：動詞故事（共 4 篇）

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 14-1 | [14-common-verbs-1-daily.md](14-common-verbs-1-daily.md) | 日常動作動詞 | ~25 | 《忙碌的一天》 |
| 14-2 | [14-common-verbs-2-movement.md](14-common-verbs-2-movement.md) | 移動動詞 | ~25 | 《運動會大冒險》 |
| 14-3 | [14-common-verbs-3-communication.md](14-common-verbs-3-communication.md) | 溝通動詞 | ~25 | 《說話的藝術》 |
| 14-4 | [14-common-verbs-4-thinking.md](14-common-verbs-4-thinking.md) | 思考與感受動詞 | ~22 | 《腦袋裡的小劇場》 |

### 第五類：興趣與社會

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 17 | [17-sports-and-hobbies.md](17-sports-and-hobbies.md) | 運動與嗜好 | 35 | 《超級運動員選拔賽》 |
| 18 | [18-technology-and-communication.md](18-technology-and-communication.md) | 科技與通訊 | 30 | 《機器人好朋友》 |
| 19 | [19-shopping-and-money.md](19-shopping-and-money.md) | 購物與金錢 | 25 | 《小小老闆開店記》 |

### 第六類：形容詞故事（共 4 篇）

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 20-1 | [20-adjectives-1-size-shape.md](20-adjectives-1-size-shape.md) | 形容詞：大小形狀 | ~20 | 《大巨人和小精靈》 |
| 20-2 | [20-adjectives-2-feelings.md](20-adjectives-2-feelings.md) | 形容詞：感受 | ~20 | 《感覺調色盤》 |
| 20-3 | [20-adjectives-3-quality.md](20-adjectives-3-quality.md) | 形容詞：品質特徵 | ~20 | 《好壞國王的比賽》 |
| 20-4 | [20-adjectives-4-other.md](20-adjectives-4-other.md) | 形容詞：其他 | ~20 | 《形容詞魔法師》 |

### 第七類：進階聽力

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 21 | [21-prepositions-and-directions.md](21-prepositions-and-directions.md) | 介系詞與方向 | 45 | 《藏寶圖大冒險》 |
| 22 | [22-common-nouns.md](22-common-nouns.md) | 常見名詞 | 70 | 《日常用品大集合》 |
| 23 | [23-social-words-and-phrases.md](23-social-words-and-phrases.md) | 社交用語 | 35 | 《有禮貌的小明》 |

### 第八類：補充故事（共 4 篇）

| 編號 | 檔案 | 主題 | 單字數 | 故事名稱 |
|------|------|------|--------|----------|
| 24-1 | [24-bonus-1-connectors.md](24-bonus-1-connectors.md) | 連接詞與副詞 | ~42 | 《因為所以大挑戰》 |
| 24-2 | [24-bonus-2-more-verbs.md](24-bonus-2-more-verbs.md) | 更多動詞 | ~58 | 《動作大王比賽》 |
| 24-3 | [24-bonus-3-more-nouns.md](24-bonus-3-more-nouns.md) | 更多名詞 | ~50 | 《名詞博物館》 |
| 24-4 | [24-bonus-4-more-adjectives.md](24-bonus-4-more-adjectives.md) | 更多形容詞 | ~50 | 《形容詞嘉年華》 |

---

## 聆聽模式

| 模式 | 說明 | 適合情境 |
|------|------|----------|
| 🎧 純聽模式 | TTS 朗讀完整故事，孩子只需聆聽 | 睡前故事、車上聽 |
| 🔁 跟讀模式 | 每句暫停，孩子跟著唸，ASR 辨識發音 | 主動學習時間 |
| ❓ 問答模式 | 故事分段播放，每段後出選擇題 | 測驗聽力理解 |
| 🎤 挑戰模式 | 播放英文單字音檔，孩子說出中文意思 | 進階複習 |

---

## 建議聆聽順序

1. **啟蒙期**：動物 (04)、食物 (03)、顏色 (05) — 最具體有趣的主題
2. **生活期**：家庭 (01)、身體 (02)、衣服 (08)、感覺 (13)
3. **探索期**：學校 (10)、居家 (09)、交通 (12)、天氣 (11)
4. **進階期**：動詞系列 (14-1~4)、形容詞系列 (20-1~4)
5. **挑戰期**：其餘主題依興趣選聽

---

## 資料來源

所有單字來自 [`1200-essential-english-words-with-chinese.md`](../1200-essential-english-words-with-chinese.md)
