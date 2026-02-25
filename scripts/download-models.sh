#!/usr/bin/env bash
# =============================================================================
# 模型下載腳本 — 預下載 ZGX Nano 所需的所有模型權重
#
# 模型清單:
#   1. Qwen3-30B (翻譯) — ~60GB FP16
#   2. Qwen3-ASR-0.6B (語音辨識) — ~1.2GB
#   3. CosyVoice2-0.5B (語音合成) — ~3GB
#   4. Flux.1-schnell (圖像生成) — ~16-22GB
#   5. Piper TTS (備用 CPU TTS) — ~100MB
#
# 使用方式:
#   bash scripts/download-models.sh [all|translation|asr|tts|flux|piper]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/models"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $*"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*"; }
section() { echo -e "\n${BLUE}========== $* ==========${NC}"; }

# 確保 huggingface-cli 可用
ensure_hf_cli() {
    if ! command -v huggingface-cli &>/dev/null; then
        log "安裝 huggingface_hub..."
        pip install -U huggingface_hub[cli]
    fi
}

# =============================================================================
# 1. Qwen3-30B — 翻譯模型 (FP16, ~60GB)
# =============================================================================
download_translation() {
    section "下載 Qwen3-30B 翻譯模型"
    ensure_hf_cli

    local MODEL_ID="Qwen/Qwen3-30B"
    local TARGET_DIR="$MODELS_DIR/Qwen3-30B"

    if [[ -d "$TARGET_DIR" ]] && [[ -f "$TARGET_DIR/config.json" ]]; then
        log "Qwen3-30B 已存在: $TARGET_DIR"
        return
    fi

    log "下載 $MODEL_ID → $TARGET_DIR"
    log "預估大小: ~60GB，請確保有足夠磁碟空間"

    huggingface-cli download "$MODEL_ID" \
        --local-dir "$TARGET_DIR" \
        --local-dir-use-symlinks False

    log "Qwen3-30B 下載完成"
    du -sh "$TARGET_DIR" | awk '{print "大小: " $1}'
}

# =============================================================================
# 2. Qwen3-ASR-0.6B — 語音辨識模型
# =============================================================================
download_asr() {
    section "下載 Qwen3-ASR-0.6B 語音辨識模型"
    ensure_hf_cli

    local MODEL_ID="Qwen/Qwen3-ASR-0.6B"
    local TARGET_DIR="$MODELS_DIR/Qwen3-ASR-0.6B"

    if [[ -d "$TARGET_DIR" ]] && [[ -f "$TARGET_DIR/config.json" ]]; then
        log "Qwen3-ASR-0.6B 已存在: $TARGET_DIR"
        return
    fi

    log "下載 $MODEL_ID → $TARGET_DIR"
    huggingface-cli download "$MODEL_ID" \
        --local-dir "$TARGET_DIR" \
        --local-dir-use-symlinks False

    log "Qwen3-ASR-0.6B 下載完成"
    du -sh "$TARGET_DIR" | awk '{print "大小: " $1}'
}

# =============================================================================
# 3. CosyVoice2-0.5B — GPU 語音合成
# =============================================================================
download_tts() {
    section "下載 CosyVoice2-0.5B 語音合成模型"
    ensure_hf_cli

    local MODEL_ID="FunAudioLLM/CosyVoice2-0.5B"
    local TARGET_DIR="$MODELS_DIR/CosyVoice2-0.5B"

    if [[ -d "$TARGET_DIR" ]]; then
        log "CosyVoice2-0.5B 已存在: $TARGET_DIR"
        return
    fi

    log "下載 $MODEL_ID → $TARGET_DIR"
    huggingface-cli download "$MODEL_ID" \
        --local-dir "$TARGET_DIR" \
        --local-dir-use-symlinks False

    log "CosyVoice2-0.5B 下載完成"
    du -sh "$TARGET_DIR" | awk '{print "大小: " $1}'
}

# =============================================================================
# 4. Flux.1-schnell — 圖像生成模型
# =============================================================================
download_flux() {
    section "下載 Flux.1-schnell 圖像生成模型"
    ensure_hf_cli

    local MODEL_ID="black-forest-labs/FLUX.1-schnell"
    local TARGET_DIR="$MODELS_DIR/FLUX.1-schnell"

    if [[ -d "$TARGET_DIR" ]] && [[ -f "$TARGET_DIR/flux1-schnell.safetensors" || -d "$TARGET_DIR/transformer" ]]; then
        log "Flux.1-schnell 已存在: $TARGET_DIR"
        return
    fi

    log "下載 $MODEL_ID → $TARGET_DIR"
    log "預估大小: ~16-22GB"

    huggingface-cli download "$MODEL_ID" \
        --local-dir "$TARGET_DIR" \
        --local-dir-use-symlinks False

    log "Flux.1-schnell 下載完成"
    du -sh "$TARGET_DIR" | awk '{print "大小: " $1}'
}

# =============================================================================
# 5. Piper TTS — CPU 備用語音合成
# =============================================================================
download_piper() {
    section "下載 Piper TTS 語音模型"

    local PIPER_DIR="$MODELS_DIR/piper"
    local VOICE_NAME="en_US-lessac-medium"
    local VOICE_FILE="$PIPER_DIR/$VOICE_NAME.onnx"

    if [[ -f "$VOICE_FILE" ]]; then
        log "Piper TTS 語音已存在: $VOICE_FILE"
        return
    fi

    mkdir -p "$PIPER_DIR"
    local BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"

    log "下載 Piper TTS 語音: $VOICE_NAME"
    wget -q --show-progress -O "$VOICE_FILE" "$BASE_URL/$VOICE_NAME.onnx"
    wget -q --show-progress -O "$VOICE_FILE.json" "$BASE_URL/$VOICE_NAME.onnx.json"

    log "Piper TTS 下載完成"
}

# =============================================================================
# 顯示摘要
# =============================================================================
show_summary() {
    section "模型下載摘要"

    echo ""
    echo "模型目錄: $MODELS_DIR"
    echo ""

    if [[ -d "$MODELS_DIR" ]]; then
        echo "已下載的模型:"
        for dir in "$MODELS_DIR"/*/; do
            if [[ -d "$dir" ]]; then
                local name=$(basename "$dir")
                local size=$(du -sh "$dir" 2>/dev/null | awk '{print $1}')
                printf "  %-35s %s\n" "$name" "$size"
            fi
        done
        echo ""
        echo "總計: $(du -sh "$MODELS_DIR" 2>/dev/null | awk '{print $1}')"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    section "ZGX Nano 模型下載"
    log "模型目錄: $MODELS_DIR"

    mkdir -p "$MODELS_DIR"

    case "${1:-all}" in
        translation) download_translation ;;
        asr)         download_asr ;;
        tts)         download_tts ;;
        flux)        download_flux ;;
        piper)       download_piper ;;
        all)
            download_asr
            download_translation
            download_tts
            download_flux
            download_piper
            ;;
        summary)     show_summary; return ;;
        *)
            echo "Usage: $0 {all|translation|asr|tts|flux|piper|summary}"
            exit 1
            ;;
    esac

    show_summary
}

main "${1:-all}"
