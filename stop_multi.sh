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
echo -e "${BOLD_CYAN}         AquaRAG 多知識系統停止管理工具              ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Find PIDs using port 8001
PIDS=$(lsof -t -i :8001)

if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}偵測到 AquaRAG 多知識後端服務正在運行 (PIDs: $PIDS)...${RESET}"
    echo -e "正在發送終止訊號 (kill)..."
    kill $PIDS 2>/dev/null
    
    # Wait up to 3 seconds for graceful shutdown
    SUCCESS=false
    for i in {1..3}; do
        PIDS_STILL=$(lsof -t -i :8001)
        if [ -z "$PIDS_STILL" ]; then
            SUCCESS=true
            break
        fi
        sleep 1
    done
    
    if [ "$SUCCESS" = false ]; then
        PIDS_STILL=$(lsof -t -i :8001)
        echo -e "${BOLD_YELLOW}服務未在時間內響應關閉，執行強制終止 (kill -9 $PIDS_STILL)...${RESET}"
        kill -9 $PIDS_STILL 2>/dev/null
        sleep 1
    fi
    
    # Final check
    PIDS_FINAL=$(lsof -t -i :8001)
    if [ -z "$PIDS_FINAL" ]; then
        echo -e "\n${BOLD_GREEN}====================================================${RESET}"
        echo -e "${BOLD_GREEN}     🎉 AquaRAG 多知識後端服務已成功停止關閉！${RESET}"
        echo -e "===================================================="
    else
        echo -e "${BOLD_RED}錯誤: 無法終止程序 (PIDs: $PIDS_FINAL)，請手動檢查！${RESET}"
        exit 1
    fi
else
    echo -e "${GREEN}沒有偵測到佔用連接埠 8001 的服務，服務目前未運行。${RESET}"
fi
