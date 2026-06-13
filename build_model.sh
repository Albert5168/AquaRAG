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
echo -e "${BOLD_CYAN}        AquaRAG 智慧養殖樹狀模型建置器              ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. 執行決定樹模型訓練與代碼生成
echo -e "\n${BOLD_CYAN}[1/2] 正在訓練平衡決定樹模型並生成對應代碼...${RESET}"
echo -e "執行指令: python3 build_decision_model.py"
python3 build_decision_model.py
if [ $? -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: 模型建置與訓練失敗！${RESET}"
    exit 1
fi

# 2. 模型邏輯功能性測試驗證
echo -e "\n${BOLD_CYAN}[2/2] 正在測試生成之決策模型 (aquaculture_rules.py)...${RESET}"

# Create a temporary python test script
cat << 'EOF' > test_rules.py
import sys
try:
    from aquaculture_rules import predict_action
    
    # 測試案例 1: 正常環境 (溶氧量充足)
    res1 = predict_action(do_val=6.50, temp_val=25.00, ph_val=7.50)
    # 測試案例 2: 警告環境 (溶氧量偏低)
    res2 = predict_action(do_val=4.20, temp_val=25.00, ph_val=7.50)
    # 測試案例 3: 危急環境 (溶氧量極低)
    res3 = predict_action(do_val=2.50, temp_val=25.00, ph_val=7.50)
    
    actions = ["全部設備關閉 (正常)", "開啟打氣機 (警告)", "開啟水車與打氣機 (危急)"]
    
    print(f"  - 測試 1 (DO 6.5, Temp 25, pH 7.5) -> 預期結果: 0 | 實際決策: {res1} ({actions[res1]})")
    print(f"  - 測試 2 (DO 4.2, Temp 25, pH 7.5) -> 預期結果: 1 | 實際決策: {res2} ({actions[res2]})")
    print(f"  - 測試 3 (DO 2.5, Temp 25, pH 7.5) -> 預期結果: 2 | 實際決策: {res3} ({actions[res3]})")
    
    if res1 == 0 and res2 == 1 and res3 == 2:
        print("  => 決定樹決策測試 100% 成功！")
        sys.exit(0)
    else:
        print("  => 錯誤: 部分決策預測不符預期！")
        sys.exit(1)
except Exception as e:
    print(f"測試執行發生例外: {e}")
    sys.exit(1)
EOF

python3 test_rules.py
TEST_RES=$?
rm test_rules.py

if [ $TEST_RES -ne 0 ]; then
    echo -e "${BOLD_RED}錯誤: 決策樹測試驗證未通過！${RESET}"
    exit 1
fi

echo -e "\n${BOLD_GREEN}====================================================${RESET}"
echo -e "${BOLD_GREEN}   🎉 智慧養殖決定樹模型訓練、生成與驗證全部完成！${RESET}"
echo -e "===================================================="
echo -e "  - Python 伺服端決策腳本: ${GREEN}aquaculture_rules.py${RESET}"
echo -e "  - ESP32 邊緣端 C++ 代碼:  ${GREEN}esp32_controller.ino${RESET}"
echo -e "===================================================="
