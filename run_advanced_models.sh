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
echo -e "${BOLD_CYAN}       AquaRAG 進階輕量機器學習模型執行器             ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. 檢查與安裝必要的 Python 庫 (如 pandas 與 scikit-learn)
echo -e "\n${BOLD_CYAN}[1/2] 正在檢查模型依賴庫...${RESET}"
REQUIRED_PACKAGES=(pandas scikit-learn numpy statsmodels)
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    python3 -c "import $pkg" &>/dev/null
    if [ $? -ne 0 ]; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo -e "${YELLOW}偵測到缺少機器學習套件: ${MISSING_PACKAGES[*]}${RESET}"
    echo -e "正在嘗試安裝: python3 -m pip install ${MISSING_PACKAGES[*]} ..."
    python3 -m pip install "${MISSING_PACKAGES[@]}"
    if [ $? -ne 0 ]; then
        echo -e "${BOLD_RED}錯誤: 套件安裝失敗！請手動執行: python3 -m pip install ${REQUIRED_PACKAGES[*]}${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓ 套件安裝完成。${RESET}"
else
    echo -e "${GREEN}✓ 所有機器學習依賴套件已就緒。${RESET}"
fi

# 2. 執行模型演示
echo -e "\n${BOLD_CYAN}[2/2] 正在運行輕量級模型預估與測試...${RESET}"
echo -e "執行指令: python3 aquaculture_advanced_models.py"
echo -e "----------------------------------------------------"
python3 aquaculture_advanced_models.py
RUN_RES=$?
echo -e "----------------------------------------------------"

if [ $RUN_RES -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: aquaculture_advanced_models.py 執行失敗！${RESET}"
    exit 1
fi

echo -e "\n執行指令: python3 aquaculture_time_series.py"
echo -e "----------------------------------------------------"
python3 aquaculture_time_series.py
RUN_RES_TS=$?
echo -e "----------------------------------------------------"

if [ $RUN_RES_TS -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: aquaculture_time_series.py 執行失敗！${RESET}"
    exit 1
fi

echo -e "\n執行指令: python3 sql_model_pipeline.py"
echo -e "----------------------------------------------------"
python3 sql_model_pipeline.py
RUN_RES_SQL=$?
echo -e "----------------------------------------------------"

if [ $RUN_RES_SQL -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: sql_model_pipeline.py 執行失敗！${RESET}"
    exit 1
fi

echo -e "\n${BOLD_GREEN}====================================================${RESET}"
echo -e "${BOLD_GREEN} 🎉 所有輕量級、時間序列與 SQL 資料庫模型執行成功！${RESET}"
echo -e "===================================================="
