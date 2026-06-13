#!/bin/bash

# Define Colors
GREEN='\033[0;32m'
BOLD_GREEN='\033[1;32m'
YELLOW='\033[0;33m'
BOLD_YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD_RED='\033[1;31m'
CYAN='\033[0;36m'
BOLD_CYAN='\033[1;36m'
RESET='\033[0m'

# Print Header
echo -e "${BOLD_CYAN}====================================================${RESET}"
echo -e "${BOLD_CYAN}         Qwen-2.5 模型壓縮與切換管理工具            ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Show Options
echo -e "請選擇您要切換的模型壓縮等級（數字越小，模型越小，生成速度越快）："
echo -e "  [1] ${BOLD_GREEN}無額外壓縮${RESET} (標準 7B, 4-bit 量化, 約 4.7GB) -> qwen2.5"
echo -e "  [2] ${BOLD_GREEN}輕量化壓縮${RESET} (精簡 3B, 4-bit 量化, 約 1.9GB) -> qwen2.5:3b"
echo -e "  [3] ${BOLD_GREEN}高度化壓縮${RESET} (極輕 1.5B, 4-bit 量化, 約 986MB) -> qwen2.5:1.5b"
echo -e "  [4] ${BOLD_GREEN}極限速度壓縮${RESET} (微型 0.5B, 4-bit 量化, 約 397MB) -> qwen2.5:0.5b"
echo -e "  [5] ${BOLD_YELLOW}深度量化壓縮${RESET} (標準 7B 進行 2-bit 深度壓縮, 約 2.5GB) -> qwen2.5:7b-instruct-q2_K"
echo -e "  [6] 取消並退出"

read -p "請輸入選擇 [1-6]: " OPTION

case $OPTION in
    1)
        MODEL_NAME="qwen2.5"
        DESCRIPTION="標準 7B 模型 (4-bit 量化)"
        ;;
    2)
        MODEL_NAME="qwen2.5:3b"
        DESCRIPTION="輕量 3B 模型 (4-bit 量化)"
        ;;
    3)
        MODEL_NAME="qwen2.5:1.5b"
        DESCRIPTION="極輕 1.5B 模型 (4-bit 量化)"
        ;;
    4)
        MODEL_NAME="qwen2.5:0.5b"
        DESCRIPTION="微型 0.5B 模型 (4-bit 量化)"
        ;;
    5)
        MODEL_NAME="qwen2.5:7b-instruct-q2_K"
        DESCRIPTION="7B 模型 (2-bit 深度量化壓縮)"
        ;;
    *)
        echo -e "${YELLOW}已取消操作。${RESET}"
        exit 0
        ;;
esac

echo -e "\n${BOLD_CYAN}您選擇了: $DESCRIPTION ($MODEL_NAME)${RESET}"

# 1. 確認 Ollama 狀態
echo -e "確認 Ollama 服務狀態..."
OLLAMA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434 2>/dev/null || echo "000")
if [ "$OLLAMA_STATUS" = "000" ]; then
    echo -e "${BOLD_RED}錯誤: Ollama 服務未啟動！請先開啟 Ollama。${RESET}"
    exit 1
fi

# 2. 自動拉取模型
echo -e "檢查本地是否存在模型 $MODEL_NAME，若無將自動下載..."
ollama pull $MODEL_NAME

# 3. 寫入環境設定檔
echo -e "\n正在寫入環境設定至 .env 檔案..."
echo "OLLAMA_MODEL=$MODEL_NAME" > .env
echo -e "${GREEN}✓ 設定已儲存 (OLLAMA_MODEL=$MODEL_NAME)。${RESET}"

# 4. 自動調用重啟腳本
echo -e "\n${BOLD_YELLOW}正在調用重啟腳本以載入新模型...${RESET}"
if [ -f "./restart.sh" ]; then
    ./restart.sh
else
    echo -e "${YELLOW}找不到 restart.sh，請手動重啟 FastAPI 服務並設定環境變數 OLLAMA_MODEL=$MODEL_NAME。${RESET}"
fi
