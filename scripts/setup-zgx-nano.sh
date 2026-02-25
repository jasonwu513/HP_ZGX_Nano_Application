#!/usr/bin/env bash
# =============================================================================
# HP ZGX Nano 自動化部署腳本
# 設置 Ubuntu 環境、NVIDIA 驅動、CUDA、Python 環境、chinese2English 服務
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
C2E_DIR="$PROJECT_ROOT/chinese2English"
LOG_FILE="$PROJECT_ROOT/setup.log"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"; }
section() { echo -e "\n${BLUE}========== $* ==========${NC}" | tee -a "$LOG_FILE"; }

# =============================================================================
# Step 0: 前置檢查
# =============================================================================
check_prerequisites() {
    section "前置檢查"

    if [[ $EUID -eq 0 ]]; then
        error "請勿使用 root 執行此腳本（會在需要時使用 sudo）"
        exit 1
    fi

    log "作業系統: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
    log "核心版本: $(uname -r)"
    log "記憶體: $(free -h | awk '/Mem:/ {print $2}')"
    log "磁碟空間: $(df -h / | awk 'NR==2 {print $4}') 可用"

    # 檢查是否為 ZGX Nano（透過 GPU 資訊）
    if command -v nvidia-smi &>/dev/null; then
        log "NVIDIA 驅動已安裝:"
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | tee -a "$LOG_FILE"
    else
        warn "未偵測到 NVIDIA 驅動，將在後續步驟安裝"
    fi
}

# =============================================================================
# Step 1: 系統更新與基礎工具
# =============================================================================
setup_system() {
    section "系統更新與基礎工具"

    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        wget \
        htop \
        nvtop \
        tmux \
        unzip \
        software-properties-common \
        libasound2-dev \
        portaudio19-dev \
        libopenblas-dev \
        pulseaudio-utils \
        libpulse0 \
        ffmpeg

    log "系統基礎工具安裝完成"
}

# =============================================================================
# Step 2: NVIDIA 驅動與 CUDA
# =============================================================================
setup_nvidia() {
    section "NVIDIA 驅動與 CUDA"

    if command -v nvidia-smi &>/dev/null; then
        log "NVIDIA 驅動已存在，跳過安裝"
        nvidia-smi | tee -a "$LOG_FILE"
        return
    fi

    log "安裝 NVIDIA 驅動..."
    sudo apt-get install -y nvidia-driver-560
    warn "NVIDIA 驅動安裝完成，可能需要重啟系統"
    warn "重啟後請重新執行此腳本"

    # 檢查 CUDA toolkit
    if ! command -v nvcc &>/dev/null; then
        log "安裝 CUDA Toolkit..."
        sudo apt-get install -y nvidia-cuda-toolkit
    fi

    log "NVIDIA 設置完成"
}

# =============================================================================
# Step 3: Python 環境
# =============================================================================
setup_python() {
    section "Python 環境設置"

    # 確保 Python 3.12+
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log "Python 版本: $PYTHON_VERSION"

    # 建立虛擬環境
    VENV_DIR="$C2E_DIR/.venv"
    if [[ ! -d "$VENV_DIR" ]]; then
        log "建立虛擬環境: $VENV_DIR"
        python3 -m venv "$VENV_DIR"
    else
        log "虛擬環境已存在: $VENV_DIR"
    fi

    # 啟用虛擬環境
    source "$VENV_DIR/bin/activate"

    # 升級 pip
    pip install --upgrade pip

    # 安裝 Server 依賴
    log "安裝 Server 依賴..."
    pip install -r "$C2E_DIR/requirements-server.txt"

    # 安裝額外的 ZGX Nano 依賴
    log "安裝 ZGX Nano 額外依賴..."
    pip install \
        sacrebleu \
        psutil \
        GPUtil \
        matplotlib \
        pandas

    log "Python 環境設置完成"
}

# =============================================================================
# Step 4: 配置 ZGX Nano 環境變數
# =============================================================================
setup_env() {
    section "配置環境變數"

    ZGX_ENV="$C2E_DIR/zgx-nano/.env.zgx-nano"

    if [[ -f "$ZGX_ENV" ]]; then
        log "ZGX Nano 環境配置已存在: $ZGX_ENV"
    else
        warn "ZGX Nano 環境配置不存在，請先建立"
    fi

    # 建立 symlink（如果不存在）
    if [[ -f "$ZGX_ENV" ]] && [[ ! -L "$C2E_DIR/.env" ]]; then
        log "備份原有 .env"
        cp "$C2E_DIR/.env" "$C2E_DIR/.env.backup.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
        log "連結 ZGX Nano 環境配置"
        ln -sf "$ZGX_ENV" "$C2E_DIR/.env"
    fi

    log "環境變數配置完成"
}

# =============================================================================
# Step 5: 驗證安裝
# =============================================================================
verify_installation() {
    section "驗證安裝"

    source "$C2E_DIR/.venv/bin/activate"

    # 檢查 PyTorch CUDA
    log "檢查 PyTorch CUDA 支援..."
    python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
    print(f'GPU Memory: {mem:.1f} GB')
" 2>&1 | tee -a "$LOG_FILE"

    # 跑測試
    log "執行 chinese2English 測試..."
    cd "$C2E_DIR"
    PYTHONPATH=. python -m pytest tests/ -v --tb=short 2>&1 | tail -20 | tee -a "$LOG_FILE"

    log "驗證完成"
}

# =============================================================================
# Step 6: 建立 systemd 服務（可選）
# =============================================================================
setup_systemd_service() {
    section "建立 systemd 服務（可選）"

    SERVICE_FILE="/etc/systemd/system/c2e-server.service"

    if [[ -f "$SERVICE_FILE" ]]; then
        log "systemd 服務已存在"
        return
    fi

    cat <<EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Chinese2English AI Translation Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$C2E_DIR
Environment=PATH=$C2E_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$C2E_DIR/.env
ExecStart=$C2E_DIR/.venv/bin/python -m server.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    log "systemd 服務已建立: c2e-server.service"
    log "啟用: sudo systemctl enable c2e-server"
    log "啟動: sudo systemctl start c2e-server"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "" > "$LOG_FILE"
    section "HP ZGX Nano 自動化部署開始"
    log "專案路徑: $PROJECT_ROOT"
    log "日誌檔案: $LOG_FILE"

    check_prerequisites
    setup_system
    setup_nvidia
    setup_python
    setup_env
    verify_installation
    setup_systemd_service

    section "部署完成"
    log "下一步:"
    log "  1. 執行模型下載: bash scripts/download-models.sh"
    log "  2. 啟動服務: cd chinese2English && source .venv/bin/activate && python -m server.main"
    log "  3. 執行效能測試: bash scripts/benchmark.sh"
}

# 支援單步執行
case "${1:-all}" in
    system)   setup_system ;;
    nvidia)   setup_nvidia ;;
    python)   setup_python ;;
    env)      setup_env ;;
    verify)   verify_installation ;;
    service)  setup_systemd_service ;;
    all)      main ;;
    *)        echo "Usage: $0 {all|system|nvidia|python|env|verify|service}" ;;
esac
