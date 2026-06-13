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
echo -e "${BOLD_CYAN}        AquaRAG 多知識庫資料匯入工具                 ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. 檢查檔案與環境
echo -e "\n${BOLD_CYAN}[1/3] 正在檢查匯入環境與文件目錄...${RESET}"

DOCS_DIR="webpage_docs"
if [ ! -d "$DOCS_DIR" ]; then
    echo -e "${BOLD_RED}錯誤: 找不到原始文件資料夾 '$DOCS_DIR'！請確認資料夾存在。${RESET}"
    exit 1
fi

DOC_COUNT=$(find "$DOCS_DIR" -name "*.docx" | wc -l | tr -d ' ')
if [ "$DOC_COUNT" -eq 0 ]; then
    echo -e "${BOLD_RED}錯誤: 資料夾 '$DOCS_DIR' 下沒有任何 docx 檔案！請放至至少一個 docx 檔案。${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ 找到 $DOC_COUNT 個待匯入的 Word 技術手冊。${RESET}"

# 檢查 Ollama 向量模型 API
OLLAMA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434 2>/dev/null || echo "000")
if [ "$OLLAMA_STATUS" = "000" ]; then
    echo -e "${BOLD_RED}錯誤: Ollama 服務未啟動！${RESET}"
    echo -e "${YELLOW}請先開啟 Ollama 應用程式，或於終端機執行: ollama serve${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama 向量服務已啟動。${RESET}"

# 2. 執行解析
echo -e "\n${BOLD_CYAN}[2/3] 正在解析 Word 檔案與段落...${RESET}"
echo -e "執行指令: python3 multi_parser.py"
python3 multi_parser.py
if [ $? -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: multi_parser.py 執行失敗！${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ 成功生成結構化 JSON (parsed_multi_docs.json)。${RESET}"

# 3. 執行向量化並寫入資料庫
echo -e "\n${BOLD_CYAN}[3/3] 正在計算文字語意向量並匯入 SQLite...${RESET}"
echo -e "執行指令: python3 multi_embedder.py"
python3 multi_embedder.py
if [ $? -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: multi_embedder.py 向量化寫入資料庫失敗！${RESET}"
    exit 1
fi

DB_ROWS=$(python3 -c "import sqlite3; conn = sqlite3.connect('multi_knowledge.db'); print(conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0])" 2>/dev/null || echo "0")

echo -e "\n${BOLD_GREEN}====================================================${RESET}"
echo -e "${BOLD_GREEN}       🎉 成功將手冊段落資料匯入多知識 RAG 系統！${RESET}"
echo -e "===================================================="
echo -e "  - 向量資料庫: ${GREEN}multi_knowledge.db${RESET}"
echo -e "  - 匯入段落總數: ${GREEN}${DB_ROWS} 區塊${RESET}"
echo -e "  - 可立即用於: ${GREEN}qwen2.5 進行檢索對答 (RAG)${RESET}"
echo -e "===================================================="
