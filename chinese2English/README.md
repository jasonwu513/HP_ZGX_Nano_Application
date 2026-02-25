# 中英學習工具 (Chinese2English)

透過樹莓派錄製日常中文對話，傳送到 GPU 伺服器進行語音辨識、翻譯、語音合成，幫助小孩學習英語。

## 架構

```
樹莓派 4 (Client)                          GPU 伺服器 (Server)
┌──────────────────────┐                   ┌─────────────────────────────────┐
│ XVF3800 → PyAudio    │                   │  FastAPI (單一進程, async)      │
│       ↓              │    WebSocket      │                                 │
│   TEN-VAD            │ ──── /ws ───────→ │  WSHandler → Pipeline Manager  │
│   (語音偵測)         │                   │     ↓            ↓              │
│       ↓              │    HTTP           │  ASR (Qwen3-ASR-0.6B)          │
│   Segment Sender     │ ── /batch ──────→ │     ↓                           │
│       ↓              │                   │  Translation (Qwen3-1.7B)       │
│   Audio Player       │ ←── 音訊串流 ──── │     ↓                           │
│   (sounddevice)      │                   │  TTS (Piper / edge / CosyVoice)│
└──────────────────────┘                   └─────────────────────────────────┘
```

## 兩種模式

| | Mode 1: 即時翻譯 | Mode 2: 批次錄音 |
|---|---|---|
| 通訊 | WebSocket `/ws` | HTTP POST `/batch` |
| 流程 | VAD 偵測句尾 → 逐句送出 → 即時播放英文 | 持續錄音 → 一次送出 → 回傳直譯 + 兒童故事版 |
| 延遲 | 低（串流） | 高（等待全部處理完） |
| 適用情境 | 日常對話即時翻譯 | 錄完一段話後產出學習素材 |

## 專案結構

```
chinese2English/
├── server/                      # GPU 伺服器端
│   ├── main.py                  # FastAPI 進入點, lifespan 載入模型
│   ├── config.py                # Pydantic Settings (env: C2E_*)
│   ├── pipeline.py              # ASR→Translation→TTS 編排, 優先佇列
│   ├── modules/
│   │   ├── asr.py               # Qwen3-ASR-0.6B 語音辨識
│   │   ├── translation.py       # Qwen3-1.7B 本地中翻英 (單句 + 批次)
│   │   └── tts/                 # TTS 語音合成 (可選後端)
│   │       ├── __init__.py      #   dispatch layer (load/synthesize/synthesize_full)
│   │       ├── _base.py         #   TTSBackend ABC
│   │       ├── _piper.py        #   Piper TTS — CPU 離線推論 (預設)
│   │       ├── _edge.py         #   edge-tts — Microsoft Edge 線上 API
│   │       ├── _cosyvoice.py    #   CosyVoice — GPU 推論
│   │       └── _none.py         #   空操作 (停用 TTS)
│   └── routes/
│       ├── health.py            # GET /health
│       ├── realtime.py          # WebSocket /ws (Mode 1)
│       └── batch.py             # POST /batch (Mode 2)
│
├── client/                      # 樹莓派客戶端
│   ├── main.py                  # 進入點, --mode realtime|batch
│   ├── config.py                # 客戶端設定 (env: C2E_CLIENT_*)
│   ├── audio_capture.py         # pw-cat 麥克風擷取 (16kHz/int16/mono)
│   ├── vad_processor.py         # TEN-VAD 語音活動偵測狀態機
│   ├── realtime_mode.py         # Mode 1: WebSocket 即時翻譯
│   ├── batch_mode.py            # Mode 2: HTTP 批次翻譯
│   ├── audio_player.py          # sounddevice 音訊播放
│   └── controller.py            # GPIO 按鈕/LED 或 CLI 選單
│
├── shared/                      # 共用模組
│   ├── constants.py             # 取樣率, frame size, timeout 等常數
│   └── audio_utils.py           # WAV 編解碼, PCM 轉換
│
├── tests/
│   ├── server/                  # ASR, Translation, TTS, Pipeline 測試
│   └── client/                  # VAD 狀態機測試
│
├── models/
│   └── piper/                   # Piper ONNX 語音模型
│
├── requirements-server.txt      # GPU 伺服器依賴
├── requirements-client.txt      # 樹莓派依賴
├── .env.example                 # 環境變數範本
└── app.py                       # (舊) 原始 ASR 端點，已重構到 server/
```

## 快速開始

### GPU 伺服器

```bash
pip install -r requirements-server.txt
pip install -U git+https://github.com/TEN-framework/ten-vad.git  # VAD (client 端也需要)
cp .env.example .env
# 編輯 .env 調整模型設定（全部本地模型，無需 API Key）

# 下載 Piper 語音模型 (預設後端)
mkdir -p models/piper
curl -L -o models/piper/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -o models/piper/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

python -m server.main
```

### 樹莓派客戶端

```bash
pip install -r requirements-client.txt

# Mode 1: 即時翻譯
python -m client.main --mode realtime

# Mode 2: 批次錄音
python -m client.main --mode batch
```

### Edge 模式（x86 CPU 離線）

> **注意**：Edge 版使用較小的離線模型（SenseVoice + Qwen3-1.7B Q4 量化），實測 ASR 辨識準確度和翻譯品質明顯不如 Client/Server 版（Qwen3-ASR + Qwen3-1.7B FP16 + GPU 推論）。適合無網路環境或 demo 用途，對品質要求高建議使用 Client/Server 架構。

```bash
pip install -r requirements-edge.txt

# 下載模型（手動放到 models/ 目錄）
# - Sherpa-ONNX SenseVoice: models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/
# - Qwen3-1.7B GGUF:       models/Qwen3-1.7B-Q4_K_M.gguf
# - Piper 語音模型:         models/piper/

cp .env.example .env
# 編輯 .env 調整 C2E_EDGE_* 設定

python -m edge.main

# Debug 模式
C2E_EDGE_LOG_LEVEL=DEBUG python -m edge.main
```

Edge ASR 支援多種後端，可在 `.env` 中切換：

| 後端 | 模型 | 大小 | 特色 |
|------|------|------|------|
| `sensevoice` (預設) | SenseVoice | ~300 MB | 最快，RTF ~0.03 |
| `qwen3` | Qwen3-ASR-0.6B OpenVINO INT8 | ~1.3 GB | 辨識準確度最高，需 `pip install openvino` |
| `breeze-int8` | Breeze-ASR-25 INT8 | ~1.8 GB | 台灣口音優化 |

```bash
# .env — 切換 ASR 後端範例
C2E_EDGE_ASR_BACKEND=qwen3
C2E_EDGE_ASR_MODEL_PATH=models/Qwen3-ASR-0.6B-INT8-OpenVINO
```

## 環境變數

| 變數 | 說明 | 預設值 |
|---|---|---|
| `C2E_ASR_MODEL_ID` | ASR 模型 ID | `Qwen/Qwen3-ASR-0.6B` |
| `C2E_TRANSLATION_MODEL_ID` | 翻譯模型 ID | `Qwen/Qwen3-1.7B` |
| `C2E_TTS_BACKEND` | TTS 後端 (`piper` / `edge` / `cosyvoice` / `none`) | `piper` |
| `C2E_PIPER_VOICE` | Piper 語音模型名稱或路徑 | `en_US-lessac-medium` |
| `C2E_PIPER_DATA_DIR` | Piper 模型檔目錄 | `models/piper` |
| `C2E_EDGE_TTS_VOICE` | edge-tts 語音名稱 | `en-US-AriaNeural` |
| `C2E_COSYVOICE_MODEL_DIR` | CosyVoice 模型路徑 | `CosyVoice2-0.5B` |
| `C2E_SERVER_HOST` | 伺服器綁定地址 | `0.0.0.0` |
| `C2E_SERVER_PORT` | 伺服器埠號 | `8000` |
| `C2E_CLIENT_SERVER_URL` | WebSocket 伺服器地址 | `ws://192.168.1.100:8000` |
| `C2E_CLIENT_SERVER_HTTP_URL` | HTTP 伺服器地址 | `http://192.168.1.100:8000` |
| `C2E_CLIENT_AUDIO_DEVICE_INDEX` | 麥克風裝置索引 | (系統預設) |

## TTS 後端比較

| 後端 | 需要網路 | GPU | 延遲 | 音質 | 安裝 |
|---|---|---|---|---|---|
| **piper** (預設) | 否 | 否 (CPU) | 低 | 中 | `pip install piper-tts` + 下載 ONNX 模型 |
| **edge** | 是 | 否 | 中 | 高 | `pip install edge-tts pydub` |
| **cosyvoice** | 否 | 是 | 中 | 高 | 需獨立安裝 CosyVoice |
| **none** | — | — | — | — | 停用 TTS，pipeline 跳過語音合成 |

## GPU 記憶體需求

- Qwen3-ASR-0.6B: ~1.2 GB VRAM
- Qwen3-1.7B (翻譯): ~1.5 GB VRAM
- CosyVoice2-0.5B: ~2-3 GB VRAM (僅 `cosyvoice` 後端)
- Piper / edge-tts: 0 GB VRAM (CPU / 雲端)
- 使用 Piper 時合計約 2.7 GB，建議最低 4 GB VRAM

## 系統依賴

```bash
# TEN-VAD 需要 libc++ runtime
sudo apt install libc++1

# 音訊錄製 (client 端) 需要 PipeWire
# Ubuntu 22.04+ 預設已安裝 pw-cat
```

## 部署同步

```bash
# 同步到遠端伺服器
rsync -avz --exclude '.venv' --exclude 'venv' --exclude '__pycache__' \
  --exclude 'models' --exclude '.git' --exclude 'output' --exclude 'vendor' \
  ./ ubuntu8505:~/chinese2English/

# 重啟遠端 Edge 服務（Docker）
ssh ubuntu8505 'cd ~/chinese2English && docker compose -f docker-compose.edge.yml down && docker compose -f docker-compose.edge.yml up -d --build'
```

## 除錯

```bash
# Server 端：透過環境變數開啟 DEBUG log
C2E_LOG_LEVEL=DEBUG PYTHONPATH=. python -m server.main

# Client 端：透過 CLI 參數開啟 DEBUG log
PYTHONPATH=. python -m client.main --mode realtime --log-level DEBUG
```

Server 端 pipeline 各步驟皆有 timing log，可觀察卡在哪一步：

```
ASR 結果: 你好 (1.23s)          ← 沒出現 = 卡在 ASR
翻譯結果: Hello (2.15s)         ← 沒出現 = 卡在翻譯
TTS 完成: 1 chunks (0.85s)      ← 沒出現 = 卡在 TTS
Pipeline 逾時 (60s)             ← 超時自動恢復
```

## 測試

```bash
PYTHONPATH=. python -m pytest tests/ -v
```
