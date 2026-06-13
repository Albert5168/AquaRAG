# 打包 AquaRAG 為 macOS 執行檔 (.app) 成果報告

我們已成功將 AquaRAG 智慧養殖與歷屆試題 RAG 系統打包成獨立的 macOS 應用程式 `AquaRAG.app`。

## 產出圖示
我們為應用程式設計了專屬的 AI 魚應用程式圖示：

![AI 魚應用程式圖示](/Users/albert/.gemini/antigravity-ide/brain/6307d742-fa66-42c6-bdbc-702e2e737dc7/ai_fish_icon_1781104043905.png)

## 主要工作成果

1. **支援動態路徑與打包模式**：
   - 修改 [app.py](file:///Users/albert/Documents/RAG/app.py)，使其能透過 `sys.frozen` 自動偵測是否在打包環境中運行。
   - 資料庫檔 `rag_database.db` 在打包版中會以唯讀模式封裝於 `.app` 中，並在第一次執行時，自動複製到使用者的當前工作目錄下（若不存在），以確保資料庫能進行讀寫操作。
   - 靜態前端資源資料夾 `static` 被正確導向至 PyInstaller 的暫存路徑（`sys._MEIPASS`）。

2. **自動開啟瀏覽器**：
   - 在 `.app` 啟動 1.5 秒後，會使用 Python 的 `webbrowser` 自動在預設瀏覽器中開啟 [http://localhost:8000/](http://localhost:8000/)，讓使用者不需手動開啟瀏覽器或輸入網址。

3. **打包腳本**：
   - 建立 [build_app.sh](file:///Users/albert/Documents/RAG/build_app.sh) 打包管理工具。
   - 使用 `sips` 調整 AI 魚 PNG 的各種解析度（16x16 至 512x512@2x），並使用 macOS 的 `iconutil` 將其編譯為單一 `icon.icns` 圖示檔。
   - 自動檢測並使用 `python3 -m PyInstaller` 執行打包，整合 FastAPI, Uvicorn 等所有依賴項目。

4. **DMG 安裝映像檔打包**：
   - 使用 macOS 原生 `hdiutil` 工具，將 `AquaRAG.app` 與 `/Applications` 應用程式目錄捷徑一同封裝為一個標準安裝用的 `AquaRAG.dmg` 映像檔。

---

## 修正 DMG 執行問題 (2026-06-10 修正)

### 1. 問題分析
當使用者點擊 `AquaRAG.dmg` 並直接啟動裡面的 `AquaRAG.app`（或將其置於唯讀環境中執行）時，程式的當前工作目錄為唯讀（例如 `/Volumes/AquaRAG`）。
舊版的 [app.py](file:///Users/albert/Documents/RAG/app.py) 嘗試使用 `shutil.copy` 將內建的資料庫複製到當前工作目錄。由於目錄唯讀，此複製動作拋出 `PermissionError` 或 `OSError` 異常，導致資料庫檔案並未成功複製，並且 `DB_PATH` 指向一個不存在的路徑，進而在 UI 的歷屆試題瀏覽器中顯示**「無匹配的題目」**。

### 2. 解決方案
我們修改了 [app.py](file:///Users/albert/Documents/RAG/app.py) 中的資料庫複製與路徑判定邏輯：
- 在 `shutil.copy` 失敗（例如拋出唯讀錯誤）時，自動執行例外處理，並將 `DB_PATH` 降級指向 **`.app` 應用程式內建的唯讀資料庫路徑**（即 `default_db_path`）。
- 由於 SQLite 能以唯讀模式正常讀取該資料庫，因此即使在唯讀的 DMG 磁碟映像檔環境中執行，歷屆試題也能完美載入。

---

## 驗證與測試結果

### 1. 打包編譯測試
執行 `bash build_app.sh` 順利完成 5 大步驟：
1. 產生 macOS `.icns` 應用程式圖示。
2. 檢查與安裝 PyInstaller（使用 `--noconfirm` 自動覆寫舊檔）。
3. 驗證打包資源檔案。
4. 使用 PyInstaller 打包成 `dist/AquaRAG.app` 執行檔。
5. 透過 `hdiutil` 封裝輸出 [AquaRAG.dmg](file:///Users/albert/Documents/RAG/AquaRAG.dmg) 安裝映像檔。

### 2. 唯讀模擬測試
在唯讀環境中測試修正後的程式邏輯，系統能順利捕捉例外並降級（Fallback）使用內建資料庫載入 300 筆題目，UI 可正常呈現題目與檢索結果。
