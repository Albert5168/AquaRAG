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

echo -e "${BOLD_CYAN}====================================================${RESET}"
echo -e "${BOLD_CYAN}          AquaRAG 系統打包與編譯工具               ${RESET}"
echo -e "${BOLD_CYAN}====================================================${RESET}"

# Setup source icon path
ICON_SRC="/Users/albert/.gemini/antigravity-ide/brain/6307d742-fa66-42c6-bdbc-702e2e737dc7/ai_fish_icon_1781104043905.png"

# 1. 製作 macOS .icns 圖示
echo -e "\n${BOLD_CYAN}[1/5] 正在產生 macOS .icns 應用程式圖示...${RESET}"
if [ ! -f "$ICON_SRC" ]; then
    echo -e "${BOLD_RED}錯誤: 找不到來源 PNG 圖示: $ICON_SRC${RESET}"
    exit 1
fi

ICON_DIR="icon.iconset"
mkdir -p "$ICON_DIR"

echo "調整圖示尺寸..."
sips -s format png -z 16 16     "$ICON_SRC" --out "$ICON_DIR/icon_16x16.png"
sips -s format png -z 32 32     "$ICON_SRC" --out "$ICON_DIR/icon_16x16@2x.png"
sips -s format png -z 32 32     "$ICON_SRC" --out "$ICON_DIR/icon_32x32.png"
sips -s format png -z 64 64     "$ICON_SRC" --out "$ICON_DIR/icon_32x32@2x.png"
sips -s format png -z 128 128   "$ICON_SRC" --out "$ICON_DIR/icon_128x128.png"
sips -s format png -z 256 256   "$ICON_SRC" --out "$ICON_DIR/icon_128x128@2x.png"
sips -s format png -z 256 256   "$ICON_SRC" --out "$ICON_DIR/icon_256x256.png"
sips -s format png -z 512 512   "$ICON_SRC" --out "$ICON_DIR/icon_256x256@2x.png"
sips -s format png -z 512 512   "$ICON_SRC" --out "$ICON_DIR/icon_512x512.png"
sips -s format png -z 1024 1024 "$ICON_SRC" --out "$ICON_DIR/icon_512x512@2x.png"

echo "編譯為 icon.icns..."
iconutil -c icns "$ICON_DIR"
rm -rf "$ICON_DIR"

if [ -f "icon.icns" ]; then
    echo -e "${GREEN}✓ icon.icns 圖示檔建立成功。${RESET}"
else
    echo -e "${BOLD_RED}錯誤: icon.icns 建立失敗！${RESET}"
    exit 1
fi

# 2. 檢查與安裝 PyInstaller
echo -e "\n${BOLD_CYAN}[2/5] 正在檢查 PyInstaller 安裝狀態...${RESET}"
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo -e "${YELLOW}未偵測到 pyinstaller，正在透過 pip 安裝...${RESET}"
    python3 -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo -e "${BOLD_RED}錯誤: PyInstaller 安裝失敗！${RESET}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ PyInstaller 已安裝完成。${RESET}"

# 3. 檢查打包的資源檔案
echo -e "\n${BOLD_CYAN}[3/5] 正在驗證打包資源檔案...${RESET}"
if [ ! -d "static" ]; then
    echo -e "${BOLD_RED}錯誤: 找不到 static 資料夾！${RESET}"
    exit 1
fi
if [ ! -f "rag_database.db" ]; then
    echo -e "${BOLD_YELLOW}警告: 找不到 rag_database.db。將建立一個空的資料庫檔案以便打包。${RESET}"
    touch rag_database.db
fi
echo -e "${GREEN}✓ 打包資源檢查完成。${RESET}"

# 4. 開始打包
echo -e "\n${BOLD_CYAN}[4/5] 正在使用 PyInstaller 打包成 AquaRAG.app...${RESET}"
python3 -m PyInstaller --clean --noconfirm \
            --name="AquaRAG" \
            --windowed \
            --noconsole \
            --add-data "static:static" \
            --add-data "rag_database.db:." \
            --collect-all uvicorn \
            --collect-all fastapi \
            --hidden-import=search_engine \
            --icon=icon.icns \
            app.py

if [ $? -eq 0 ] && [ -d "dist/AquaRAG.app" ]; then
    echo -e "\n${BOLD_CYAN}[5/5] 正在將 AquaRAG.app 封裝成 AquaRAG.dmg...${RESET}"
    mkdir -p dist/dmg_temp
    cp -R dist/AquaRAG.app dist/dmg_temp/
    ln -s /Applications dist/dmg_temp/Applications
    rm -f AquaRAG.dmg
    hdiutil create -volname "AquaRAG" -srcfolder dist/dmg_temp -ov -format UDZO AquaRAG.dmg &> /dev/null
    rm -rf dist/dmg_temp

    if [ -f "AquaRAG.dmg" ]; then
        echo -e "${GREEN}✓ AquaRAG.dmg 建立成功。${RESET}"
    else
        echo -e "${BOLD_RED}錯誤: AquaRAG.dmg 建立失敗！${RESET}"
        exit 1
    fi

    echo -e "\n${BOLD_GREEN}====================================================${RESET}"
    echo -e "       🎉 AquaRAG 系統打包與映像檔製作成功！"
    echo -e "===================================================="
    echo -e "  - 應用程式路徑: ${BOLD_GREEN}dist/AquaRAG.app${RESET}"
    echo -e "  - 安裝映像檔:   ${BOLD_GREEN}AquaRAG.dmg${RESET}"
    echo -e "  - 圖示:         套用專屬 AI 魚圖示"
    echo -e "===================================================="
    
    # 移除暫存的 icon.icns 檔以保持工作目錄乾淨
    rm -f icon.icns
else
    echo -e "${BOLD_RED}錯誤: 打包失敗，請檢查上述錯誤日誌。${RESET}"
    exit 1
fi
