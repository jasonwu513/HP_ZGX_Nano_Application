# AI 親子英語學習站 — HP ZGX Nano 領航者計畫

利用 HP ZGX Nano 的 128GB 統一記憶體與 1000 TOPS 算力，打造隱私優先、零月費、離線可用的家庭 AI 英語教育站。

> **為什麼做這個專案？** 新竹科學園區的教育競爭從小一就開始 — 班上超過七成的孩子在上英語補習班，每月費用 NT$10,000–25,000。女兒去了全美語補習班，回來卻說「老師講的我聽不懂」。身為工程師爸爸，我用 AI 打造 1 對 1 的課後英語助教來輔助補習班 — 讓她在家用自己的節奏複習、互動，不懂的地方反覆練習，沒有同儕壓力。

## 專案架構

```
HP_ZGX_Nano_Application/
├── chinese2English/          # 即時中翻英語音翻譯（已完成）
│   ├── server/               # FastAPI GPU Server (ASR → Translation → TTS)
│   ├── client/               # 樹莓派 Client
│   ├── edge/                 # x86 CPU 離線模式
│   ├── zgx-nano/             # ZGX Nano 專用配置
│   └── tests/                # 9 個測試檔案
│
├── vocabulary/               # 英語遊戲學習平台（設計完成 待實做）
│   ├── games/                # 32 款遊戲設計
│   ├── stories/              # 32 篇故事
│   ├── scenarios/            # 32 個場景
│   └── game_vocabulary.csv   # 12,200 詞彙資料
│
├── image-generation/         # Flux 圖卡生成 Pipeline
│   └── generate_cards.py     # 自動化批量生圖
│
├── scripts/                  # 自動化腳本
│   ├── setup-zgx-nano.sh     # 系統部署腳本
│   ├── download-models.sh    # 模型下載腳本
│   ├── benchmark.py          # 效能測試 Python 腳本
│   └── benchmark.sh          # 效能測試執行腳本
│
├── application/              # 申請書文件
│   └── APPLICATION.md        # HP ZGX Nano 領航者計畫申請書
│
└── results/                  # 效能測試結果（自動生成）
```

## 快速開始

### 1. ZGX Nano 部署

```bash
# 系統設置與依賴安裝
bash scripts/setup-zgx-nano.sh

# 下載模型（Qwen3-30B, CosyVoice2, Flux.1-schnell 等）
bash scripts/download-models.sh

# 啟動 Server
cd chinese2English
source .venv/bin/activate
python -m server.main
```

### 2. 效能測試

```bash
# 翻譯效能測試
bash scripts/benchmark.sh translation

# 完整測試
bash scripts/benchmark.sh all
```

### 3. 圖卡生成

```bash
# 生成 prompt（預覽模式）
python image-generation/generate_cards.py --dry-run

# 生成前 10 張圖卡
python image-generation/generate_cards.py --limit 10

# 生成指定類別
python image-generation/generate_cards.py --category "Animals"
```

### 4. 測試

```bash
cd chinese2English
PYTHONPATH=. python -m pytest tests/ -v
```

## ZGX Nano 技術升級摘要

| 元件 | Edge (CPU) | ZGX Nano (GPU) | 提升 |
|------|-----------|----------------|------|
| 翻譯 | Qwen3-1.7B Q4 | **Qwen3-30B FP16** | 17.6x 參數 |
| ASR | Qwen3-ASR INT8 | **Qwen3-ASR FP16** | 全精度 |
| TTS | Piper (CPU) | **CosyVoice2 (GPU)** | 自然語調 |
| 圖像 | 無 | **Flux.1-schnell** | 全新能力 |

## 記憶體預算 (128GB)

| 元件 | 用量 |
|------|------|
| Qwen3-ASR-0.6B FP16 | ~1.5GB | or Qwen3-ASR-1.7B 
| Qwen3-30B FP16 | ~60GB |
| CosyVoice2-0.5B | ~3GB |
| Flux.1-schnell | ~16-22GB |
| 系統 + PyTorch | ~5-10GB |
| **合計 / 剩餘** | **~85-97GB / ~31-43GB** |
