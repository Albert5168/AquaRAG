# AquaRAG 雲端部署指南 (Cloud Deployment Guide)

本指南說明如何將您的 **AquaRAG 系統**免費部署至雲端平台（如 **Render** 或 **Hugging Face Spaces**），取得專屬的雲端公開網址。

由於我們的系統已整合了 **Google Gemini API** 作為雲端運算核心，且資料庫採用輕量化的 **SQLite**，因此本專案**不需要**任何昂貴的 GPU 伺服器，使用免費的 CPU 方案即可流暢執行！

---

## 準備工作 (Prerequisites)

1. 將您本地的 AquaRAG 專案目錄初始化並推送到您的個人 **GitHub 儲存庫 (Repository)**。
2. 確保專案根目錄下包含以下新產生的設定檔：
   - `Dockerfile`：容器化設定檔。
   - `requirements.txt`：Python 套件依賴清單。
   - `rag_database.db` 與 `multi_knowledge.db`：已建置好的向量資料庫檔案。

---

## 方案 A：部署至 Render (推薦，最簡單)

Render 是一個熱門的雲端託管平台，提供免費額度且原生支援 Docker 部署。

### 步驟 1：部署「魚類生理學考試系統」

1. 註冊並登入 [Render 官網](https://render.com/)。
2. 點擊右上角 **New +**，選擇 **Web Service**。
3. 連結您的 GitHub 帳號，並選擇您的 **AquaRAG 專案儲存庫**。
4. 填寫服務設定：
   - **Name**: `aquarag-exam` (或自訂)
   - **Environment**: 選擇 **Docker** (Render 會自動偵測並讀取根目錄下的 `Dockerfile`)
   - **Region**: 選擇距離您最近的區域 (例如 Singapore 或 Oregon)
   - **Instance Type**: 選擇 **Free** (免費方案)
5. 點擊 **Advanced** 展開進階設定，新增環境變數 (Environment Variables)：
   - 新增 `GEMINI_API_KEY`，數值填入您的 Gemini API Key。
6. 點擊 **Create Web Service**，等待數分鐘完成建置，即可獲得公開網址 (例如 `https://aquarag-exam.onrender.com`)。

---

### 步驟 2：部署「智慧養殖多知識庫系統」

由於兩個系統共享同一個 GitHub 專案，您可以**用同一個儲存庫在 Render 上建立第二個 Web Service**！

1. 再次點擊 **New +** -> **Web Service**，選擇同一個 **AquaRAG 專案儲存庫**。
2. 填寫服務設定：
   - **Name**: `aquarag-multi` (或自訂)
   - **Environment**: 選擇 **Docker**
   - **Instance Type**: 選擇 **Free**
3. **關鍵設定**：在 **Start Command** 欄位輸入以下覆寫指令（改啟動多知識庫伺服器）：
   ```bash
   uvicorn app_multi:app --host 0.0.0.0 --port $PORT
   ```
4. 點擊 **Advanced** 新增環境變數：
   - 新增 `GEMINI_API_KEY`，數值填入您的 API Key。
5. 點擊 **Create Web Service**，建置完成後即可獲得第二個網址 (例如 `https://aquarag-multi.onrender.com`)。

---

## 方案 B：部署至 Hugging Face Spaces (100% 永久免費)

Hugging Face Spaces 提供完全免費的 Docker 容器託管服務，非常適合學術與 RAG 展示專案。

1. 註冊並登入 [Hugging Face](https://huggingface.co/)。
2. 點擊右上角個人頭像 -> **New Space**。
3. 填寫 Space 設定：
   - **Space name**: `aquarag-exam` (自訂名稱)
   - **License**: 選擇 `mit` (或任意)
   - **SDK**: 選擇 **Docker**
   - **Docker template**: 選擇 **Blank**
   - **Space hardware**: 選擇 **Cpu basic (Free)**
   - **Visibility**: 選擇 **Public** (公開) 或 **Private** (私人)
4. 點擊 **Create Space**。
5. 在建立好的 Space 頁面中，點擊 **Settings** 標籤頁：
   - 找到 **Variables and secrets** 區塊。
   - 點擊 **New secret**，Name 填入 `GEMINI_API_KEY`，Value 填入您的金鑰。
6. 將您的程式碼推送到 Hugging Face 提供的 Git 遠端倉庫（或者直接在 Hugging Face 網頁端點擊 **Files and versions** -> **Upload files** 上傳所有專案檔案，包含 `rag_database.db`、`app.py`、`static/`、`Dockerfile` 與 `requirements.txt`）。
7. 上傳完成後，Hugging Face 會自動根據 `Dockerfile` 進行 Build，完成後即可直接在 Space 中互動使用！

*(註：若要部署多知識庫，只需另建一個 Space，並在 `Dockerfile` 最後一行的 `app` 改為 `app_multi`，或在 Docker 啟動指令中覆寫即可。)*
