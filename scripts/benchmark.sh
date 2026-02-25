#!/usr/bin/env bash
# =============================================================================
# 效能測試執行腳本 — 自動偵測環境並執行對應測試
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
C2E_DIR="$PROJECT_ROOT/chinese2English"
RESULTS_DIR="$PROJECT_ROOT/results"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[benchmark]${NC} $*"; }
section() { echo -e "\n${BLUE}========== $* ==========${NC}"; }

mkdir -p "$RESULTS_DIR"

# 啟用虛擬環境
if [[ -f "$C2E_DIR/.venv/bin/activate" ]]; then
    source "$C2E_DIR/.venv/bin/activate"
fi

MODE="${1:-translation}"

section "HP ZGX Nano 效能測試"
log "模式: $MODE"
log "結果目錄: $RESULTS_DIR"

# 載入環境變數
if [[ -f "$C2E_DIR/.env" ]]; then
    set -a
    source "$C2E_DIR/.env"
    set +a
fi

cd "$C2E_DIR"

case "$MODE" in
    translation)
        python "$SCRIPT_DIR/benchmark.py" --mode translation --output "$RESULTS_DIR"
        ;;
    asr)
        python "$SCRIPT_DIR/benchmark.py" --mode asr --output "$RESULTS_DIR"
        ;;
    all)
        python "$SCRIPT_DIR/benchmark.py" --mode all --output "$RESULTS_DIR"
        ;;
    compare)
        if [[ -z "${2:-}" ]] || [[ -z "${3:-}" ]]; then
            echo "Usage: $0 compare <edge_json> <nano_json>"
            exit 1
        fi
        python "$SCRIPT_DIR/benchmark.py" --mode compare \
            --edge-json "$2" --nano-json "$3" --output "$RESULTS_DIR"
        ;;
    *)
        echo "Usage: $0 {translation|asr|all|compare <edge_json> <nano_json>}"
        exit 1
        ;;
esac

section "完成"
log "結果請見: $RESULTS_DIR/"
ls -la "$RESULTS_DIR/"
