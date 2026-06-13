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
echo -e "${BOLD_CYAN}       Qwen-2.5 專家知識庫微調 (Fine-tuning) 工具     ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. 檢查 Python 機器學習依賴套件
echo -e "\n${BOLD_CYAN}[1/3] 正在檢查與安裝機器學習依賴套件...${RESET}"
REQUIRED_PACKAGES=(torch transformers peft trl accelerate bitsandbytes datasets)
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    python3 -c "import $pkg" &>/dev/null
    if [ $? -ne 0 ]; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo -e "${YELLOW}偵測到缺少微調套件: ${MISSING_PACKAGES[*]}${RESET}"
    echo -e "正在嘗試自動執行安裝: pip install ${MISSING_PACKAGES[*]} ..."
    pip install "${MISSING_PACKAGES[@]}"
    if [ $? -ne 0 ]; then
        echo -e "${BOLD_RED}錯誤: 依賴套件安裝失敗！請手動執行: pip install ${REQUIRED_PACKAGES[*]}${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓ 套件安裝完成。${RESET}"
else
    echo -e "${GREEN}✓ 所有微調依賴套件（PyTorch、Transformers、PEFT、TRL）已就緒。${RESET}"
fi

# 2. 生成微調資料集
echo -e "\n${BOLD_CYAN}[2/3] 正在生成微調對話資料集 (JSONL)...${RESET}"
python3 prepare_dataset.py
if [ $? -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: 資料集生成失敗！請確認 parsed_questions.json 是否存在。${RESET}"
    exit 1
fi

# 3. 提示確認微調
echo -e "\n${BOLD_CYAN}[3/3] 準備執行 QLoRA 微調訓練...${RESET}"
echo -e "${BOLD_YELLOW}警告：微調 7B 模型需要高效能 GPU (建議 16GB VRAM 以上)。${RESET}"
echo -e "訓練完成後，LoRA 權重將會儲存於 ${GREEN}./qwen2.5_lora_adapter${RESET}"
echo ""

read -p "您確定要開始訓練嗎？ (y/n): " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${BOLD_GREEN}啟動訓練程序 (python3 train.py)...${RESET}"
    python3 train.py
else
    echo -e "${YELLOW}訓練已取消。您隨時可以執行本腳本啟動微調。${RESET}"
fi
