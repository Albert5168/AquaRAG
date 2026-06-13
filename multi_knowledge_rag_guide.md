# AquaRAG 多知識庫系統建置與通用文件解析技術說明書

本手冊詳細說明 AquaRAG 多知識庫 RAG 系統的架構設計、通用 Word 文件的語意切分（Chunking）演算法、向量資料庫的建置流程，以及如何透過本機 Qwen-2.5 7B 模型進行脈絡強化生成（Retrieval-Augmented Generation, RAG）。

---

## 一、 系統架構與設計理念

為了不影響原有的國家考試「魚類生理學歷屆試題專家系統」，本系統採用了**獨立並行**的模組化設計：

1. **埠口隔離 (Port Isolation)**：服務運作於連接埠 `8001`，與原系統的 `8000` 埠口完全獨立，可同時在背景執行。
2. **獨立資料庫**：新建 `multi_knowledge.db` SQLite 檔案，專門儲存技術手冊段落與向量特徵。
3. **自訂知識庫目錄**：新設 `webpage_docs/` 作為通用文檔的存放夾，支援任意數量的 `.docx` 格式網頁內容或技術說明文件。

### 系統資料流與運作拓撲：

```
[ webpage_docs/*.docx ] 
         │
         ▼ (multi_parser.py)
[ parsed_multi_docs.json ]  (語意段落切分，每段約 600-800 字)
         │
         ▼ (multi_embedder.py & Ollama nomic-embed-text)
[ multi_knowledge.db ] (SQLite 欄位包含 ID, 檔名, 標題, 內文, 向量 BLOB)
         │
         ▼ (multi_search_engine.py 在系統啟動時一次性載入記憶體)
[ Memory-Cached Vector Matrix ] (高維度矩陣點積快速比對)
         │
         ▼ (app_multi.py 接收使用者提問)
[ Retrieve Top-4 Chunks ] --> [ Context Assembly & System Prompt ]
         │
         ▼ (Ollama qwen2.5 7B 推理)
[ SSE Streaming Response ] --> [ Frontend Web UI (Port 8001) ]
```

---

## 二、 通用 Word 文件解析與語意切分 (Chunking)

原系統的 `parser.py` 是針對國家考試試題的固定格式（如「第 X 套試題：」、「第 Y 題：」）進行硬編碼解析。而在通用多知識庫中，輸入文件（如網頁內容導出的 DOCX 檔）的格式極為多樣。因此，我們實作了全新的通用文件切分器 [multi_parser.py](file:///Users/albert/Documents/RAG/multi_parser.py)：

### 2.1 標題與章節偵測
通用切分器透過以下兩種機制自動偵測文檔的章節標題：
1. **Word 內建樣式**：檢測段落的 style 名稱是否包含 `heading` 或 `title`。
2. **正規表達式與規則比對**：若段落長度小於 60 字且結尾沒有標點符號，同時開頭匹配特定格式（例如：`第X章`、`第Y節`、`1. `、`一、`），則自動將其識別為新章節的起點。

### 2.2 帶有重疊區間的滑動窗口 (Sliding Window with Overlap)
當長篇手冊的內容過長時，直接截斷會導致章節前後脈絡的破裂（例如：公式的前提條件在前一段，推導結果在後一段）。
為了維持上下文完整性，切分演算法採用了**滑動窗口與重疊（Overlap）機制**：
- **目標區塊大小 (Target Chunk Size)**：設定為約 700 字。
- **重疊大小 (Overlap Size)**：設定為約 150 字。
當前累計的段落文字超過 700 字時，切分器會切出一個 Chunk，並將該 Chunk 末尾的約 150 字（或最後 1~2 個整句/段落）保留，作為下一個 Chunk 的起點，從而完美保留了語意的過渡與連貫。

### 2.3 表格轉換
手冊中的數據對照表格透過 python-docx 讀取後，會自動在 Parser 中被轉譯為標準的 **Markdown 表格語法**，並以單一塊（Table Block）形式被併入對應的 Chunk 內，確保大型對照表不會被強行攔腰切斷，同時模型也能正確理解行列關係。

---

## 三、 SQLite 向量儲存 Schema

資料庫 `multi_knowledge.db` 的 `documents` 資料表 Schema 設計如下：

```sql
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source_file TEXT,       -- 來源 Word 檔名
    chunk_title TEXT,       -- 當前偵測到的章節/段落標題
    content TEXT,           -- 該區塊的 Markdown 內文與表格
    embedding BLOB          -- nomic-embed-text 產生的 768 維 float32 向量二進位大物件
)
```

在 [multi_embedder.py](file:///Users/albert/Documents/RAG/multi_embedder.py) 中，我們將資料拼接為特徵文字：
`"來源檔案：{source_file}\n章節標題：{chunk_title}\n段落內容：{content}"`
透過 Ollama API 計算出 768 維的 `float32` 陣列，隨後利用 NumPy 序列化為二進位 `BLOB` 寫入資料庫：

```python
import numpy as np
# 轉換為 float32 陣列 (4 bytes per float, 共 3072 bytes)
emb_arr = np.array(emb, dtype=np.float32)
emb_blob = emb_arr.tobytes()
```

---

## 四、 記憶體快取與語意檢索技術

為了提供極致的查詢反應速度，[multi_search_engine.py](file:///Users/albert/Documents/RAG/multi_search_engine.py) 採用了**記憶體快取向量矩陣**的優化技術：

### 4.1 系統啟動載入
在服務初始化時，Search Engine 會執行 `SELECT` 將所有段落的 `embedding` BLOB 一次性讀入記憶體，並透過 NumPy 的 `np.frombuffer()` 還原，再使用 `np.vstack()` 堆疊為 $N \times 768$ 的二維浮點數矩陣。如此一來，在使用者查詢時，無需進行耗時的資料庫 I/O，而能直接在記憶體中進行高速運算。

### 4.2 餘弦相似度矩陣運算
當使用者輸入查詢句時，系統透過 Ollama 取得查詢向量 $q$，並利用 NumPy 的向量化乘法計算餘弦相似度（Cosine Similarity）：

$$\text{Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$

NumPy 程式碼實作：
```python
dot_product = np.dot(self.embeddings, query_emb)
norm_a = np.linalg.norm(self.embeddings, axis=1)
norm_b = np.linalg.norm(query_emb)
similarities = dot_product / (norm_a * norm_b + 1e-8)
```
系統會根據相似度分數由高到低排序，取出 Top-4 最相關的文獻區塊。

### 4.3 離線備援（降級關鍵字搜尋）
如果本地的 Ollama 服務離線或未下載向量模型，Search Engine 會自動降級為基於空格分詞的關鍵字權重計分法，利用 `source_file` (權重 3.0)、`chunk_title` (權重 5.0) 與 `content` (權重 1.0) 進行模糊比對，確保系統在任何情況下都能提供一定的檢索能力。

---

## 五、 RAG 脈絡組裝與 SSE 串流問答

後端 API 伺服器 [app_multi.py](file:///Users/albert/Documents/RAG/app_multi.py) 使用 FastAPI 實作。當接收到 `/api/chat` 的問答請求時，RAG 的核心邏輯如下：

1. **脈絡提取**：檢索出 Top-4 關聯段落，將其檔案來源、章節名稱與內文拼接為 `context_str`。
2. **提示詞工程 (Prompt Engineering)**：將 `context_str` 嵌入至 System Prompt 中，對模型施加嚴格的行為約束：
   - 限定只能基於給定的上下文回答。
   - 必須使用繁體中文。
   - 善用 Markdown 語法（列表、表格、粗體）提升可讀性。
   - 必須進行歸納整理，禁止全文複製。
3. **SSE (Server-Sent Events) 串流發送**：
   - 首先發送 `citations` 事件，將檢索到的來源手冊名稱與標題以 JSON 格式發送給前端，在對話框中顯示文獻標籤。
   - 隨後與 Ollama 的 `/api/chat` 連接，以 `stream=True` 流式取得模型生成的字元（Tokens），並逐字以 `text` 事件發送至前端瀏覽器，提供流暢的動態輸出體驗。

---

## 六、 知識庫維護與自訂擴充指南

新系統的擴充非常直觀，任何人皆可輕鬆操作：

1. **新增手冊**：將您要擴充的任何主題 docx 文件，直接複製或拖放入專案根目錄下的 `webpage_docs/` 資料夾內。
2. **重新建立向量索引**：在終端機中執行：
   ```bash
   ./restart_multi.sh --rebuild
   ```
   腳本會引導執行：
   - 清空並重新掃描 `webpage_docs/` 資料夾。
   - 調用 `multi_parser.py` 切分段落，生成新的 `parsed_multi_docs.json`。
   - 調用 `multi_embedder.py` 向 Ollama 請求語意向量，並寫入 `multi_knowledge.db`。
   - 自動重啟 FastAPI 服務，載入最新的向量矩陣。
3. **即時生效**：刷新瀏覽器網頁，即可對新匯入的手冊內容進行語意檢索與 RAG 智能對答！
