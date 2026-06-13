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
echo -e "${BOLD_CYAN}         AquaRAG 多知識庫系統重新啟動管理工具        ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Parse arguments
REBUILD_DB=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -r|--rebuild) REBUILD_DB=true ;;
        -h|--help)
            echo "使用方法:"
            echo "  $0 [選項]"
            echo ""
            echo "選項:"
            echo "  -r, --rebuild    強制重新解析 Word 文件並重建向量資料庫"
            echo "  -h, --help       顯示此說明訊息"
            exit 0
            ;;
        *) echo -e "${BOLD_RED}未知參數: $1${RESET}"; exit 1 ;;
    esac
    shift
done

# 1. 停止現有服務
echo -e "\n${BOLD_CYAN}[1/5] 正在停止現有的 AquaRAG 多知識服務...${RESET}"
PIDS=$(lsof -t -i :8001)

if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}偵測到連接埠 8001 已被佔用 (PID: $PIDS)。正在終止程序...${RESET}"
    kill $PIDS 2>/dev/null
    sleep 1.5
    PIDS_STILL=$(lsof -t -i :8001)
    if [ -n "$PIDS_STILL" ]; then
        echo -e "${RED}程序仍未關閉，強制終止 (kill -9 $PIDS_STILL)...${RESET}"
        kill -9 $PIDS_STILL 2>/dev/null
    fi
    echo -e "${GREEN}成功停止舊服務。${RESET}"
else
    echo -e "${GREEN}沒有偵測到佔用連接埠 8001 的服務。${RESET}"
fi

# 2. 依賴環境檢查
echo -e "\n${BOLD_CYAN}[2/5] 正在檢查依賴環境與服務...${RESET}"

# Check python3
if ! command -v python3 &> /dev/null; then
    echo -e "${BOLD_RED}錯誤: 系統未安裝 python3。請先安裝 Python 3。${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 已安裝。${RESET}"

# Check Python libraries
echo -e "檢查 Python 依賴套件..."
MISSING_LIBS=()
for lib in fastapi uvicorn requests numpy docx; do
    python3 -c "import $lib" &> /dev/null
    if [ $? -ne 0 ]; then
        MISSING_LIBS+=($lib)
    fi
done

if [ ${#MISSING_LIBS[@]} -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: 缺少以下 Python 套件: ${MISSING_LIBS[*]}${RESET}"
    echo -e "${YELLOW}請執行指令安裝: pip install ${MISSING_LIBS[*]}${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ Python 依賴套件檢查通過。${RESET}"

# Check Ollama status
echo -e "檢查 Ollama 向量與語言模型服務..."
OLLAMA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434 2>/dev/null || echo "000")
if [ "$OLLAMA_STATUS" = "000" ]; then
    echo -e "${BOLD_RED}錯誤: Ollama 服務未啟動！${RESET}"
    echo -e "${YELLOW}請先開啟 Ollama 應用程式，或在終端機執行: ollama serve${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama 服務正常運作。${RESET}"

# Check Ollama models
OLLAMA_MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null || ollama list | awk 'NR>1 {print $1}')

check_model() {
    local target_model=$1
    if echo "$OLLAMA_MODELS" | grep -q "$target_model"; then
        return 0
    else
        return 1
    fi
}

# Ensure nomic-embed-text exists
if check_model "nomic-embed-text"; then
    echo -e "${GREEN}✓ 向量模型 (nomic-embed-text) 已準備就緒。${RESET}"
else
    echo -e "${YELLOW}找不到向量模型 nomic-embed-text，正在自動下載...${RESET}"
    ollama pull nomic-embed-text
fi

# Ensure qwen2.5 exists
if check_model "qwen2.5"; then
    echo -e "${GREEN}✓ 語言模型 (qwen2.5) 已準備就緒。${RESET}"
else
    echo -e "${YELLOW}找不到語言模型 qwen2.5，正在自動下載...${RESET}"
    ollama pull qwen2.5
fi

# 3. 資料庫驗證與重構
echo -e "\n${BOLD_CYAN}[3/5] 正在驗證資料庫狀態...${RESET}"
DB_EXISTS=true
if [ ! -f "multi_knowledge.db" ]; then
    echo -e "${YELLOW}警告: 找不到資料庫檔案 (multi_knowledge.db)。將自動進行初始化建置。${RESET}"
    DB_EXISTS=false
fi

if [ "$REBUILD_DB" = true ] || [ "$DB_EXISTS" = false ]; then
    echo -e "${BOLD_YELLOW}正在啟動資料庫建置/重構流程...${RESET}"
    
    echo -e "-> 步驟 1: 解析技術手冊 Word 文件..."
    python3 multi_parser.py
    if [ $? -ne 0 ]; then
        echo -e "${BOLD_RED}錯誤: multi_parser.py 執行失敗！請檢查 'webpage_docs' 下是否有 docx 檔案。${RESET}"
        exit 1
    fi
    
    echo -e "-> 步驟 2: 計算文字向量嵌入並載入資料庫..."
    python3 multi_embedder.py
    if [ $? -ne 0 ]; then
        echo -e "${BOLD_RED}錯誤: multi_embedder.py 執行失敗！請確認 Ollama 服務與向量模型是否正常運作。${RESET}"
        exit 1
    fi
    
    echo -e "${BOLD_GREEN}✓ 資料庫建置完成。${RESET}"
else
    # Quick integrity check
    DB_ROWS=$(python3 -c "import sqlite3; conn = sqlite3.connect('multi_knowledge.db'); print(conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0])" 2>/dev/null || echo "0")
    if [ "$DB_ROWS" -eq 0 ]; then
        echo -e "${BOLD_YELLOW}警告: 資料庫為空，強制重新建置...${RESET}"
        python3 multi_parser.py && python3 multi_embedder.py
    else
        echo -e "${GREEN}✓ 資料庫已就緒，包含 $DB_ROWS 筆手冊段落資料。${RESET}"
    fi
fi

# 4. 背景啟動 FastAPI
echo -e "\n${BOLD_CYAN}[4/5] 正在啟動 AquaRAG 多知識後端服務...${RESET}"
if [ -f ".env" ]; then
    echo -e "載入環境變數設定 (.env)..."
    export $(cat .env | grep -v '^#' | xargs)
fi
echo -e "執行模型: ${BOLD_GREEN}${OLLAMA_MODEL:-qwen2.5}${RESET}"
echo -e "執行指令: nohup python3 app_multi.py > app_multi.log 2>&1 &"
nohup python3 app_multi.py > app_multi.log 2>&1 &
APP_PID=$!
sleep 1

# Check if PID is still alive
if kill -0 $APP_PID 2>/dev/null; then
    echo -e "${GREEN}服務已在背景啟動 (PID: $APP_PID)，日誌輸出至 app_multi.log。${RESET}"
else
    echo -e "${BOLD_RED}錯誤: 後端服務啟動後立即結束，請檢查 app_multi.log！${RESET}"
    tail -n 15 app_multi.log
    exit 1
fi

# 5. 健康檢查
echo -e "\n${BOLD_CYAN}[5/5] 正在進行健康檢查...${RESET}"
echo -n "等待服務響應."
SUCCESS=false
for i in {1..15}; do
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/stats 2>/dev/null || echo "000")
    if [ "$STATUS_CODE" = "200" ]; then
        SUCCESS=true
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

if [ "$SUCCESS" = true ]; then
    echo -e "\n${BOLD_GREEN}====================================================${RESET}"
    echo -e "    🎉 AquaRAG 多知識庫系統已成功重啟並運行中！"
    echo -e "===================================================="
    echo -e "  - 系統網址: ${BOLD_GREEN}http://localhost:8001/${RESET}"
    echo -e "  - 後端日誌: ${GREEN}tail -f app_multi.log${RESET}"
    echo -e "===================================================="
else
    echo -e "${BOLD_RED}健康檢查失敗！服務在 15 秒內未回應。${RESET}"
    echo -e "${YELLOW}請查看日誌內容：${RESET}"
    echo -e "----------------------------------------------------"
    tail -n 20 app_multi.log
    echo -e "----------------------------------------------------"
    exit 1
fi
