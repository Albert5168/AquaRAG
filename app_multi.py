import os
import sys

# Load .env file manually if exists
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

import shutil
import sqlite3
import json
import requests
import uvicorn
import webbrowser
import zhconv
import google.generativeai as genai
from threading import Timer
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from multi_search_engine import MultiSearchEngine

# Detect if running in a PyInstaller bundle
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    is_frozen = True
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    is_frozen = False

# Resolve Database Path
DB_PATH = os.path.join(os.getcwd(), "multi_knowledge.db")
if not os.path.exists(DB_PATH):
    default_db_path = os.path.join(bundle_dir, "multi_knowledge.db")
    if os.path.exists(default_db_path):
        try:
            shutil.copy(default_db_path, DB_PATH)
        except Exception as e:
            print(f"Error copying initial database to current working directory: {e}")
            DB_PATH = default_db_path

# Resolve Static Directory Path
STATIC_DIR = os.path.join(bundle_dir, "static_multi")

app = FastAPI(title="AquaRAG 多知識庫系統")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Search Engine
search_engine = MultiSearchEngine(db_path=DB_PATH, embed_model="nomic-embed-text")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
    api_key: str = None

@app.get("/api/stats")
def get_stats():
    db_path = DB_PATH
    if not os.path.exists(db_path):
        return {
            "exam_sets_count": 0,
            "questions_count": 0,
            "db_size_mb": 0
        }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # "exam_sets_count" represents number of unique source files
    cursor.execute("SELECT COUNT(DISTINCT source_file) FROM documents")
    exam_sets_count = cursor.fetchone()[0]
    
    # "questions_count" represents total chunks
    cursor.execute("SELECT COUNT(*) FROM documents")
    questions_count = cursor.fetchone()[0]
    
    conn.close()
    
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    
    if os.getenv("GEMINI_API_KEY"):
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip().strip('"').strip("'")
        if model_id.startswith("models/"):
            model_id = model_id[7:]
        active_model = " ".join([w.capitalize() for w in model_id.split("-")])
        if "Gemini" not in active_model:
            active_model = f"Gemini {active_model}"
        active_desc = "Cloud LLM via Google API"
    else:
        active_model = "Qwen-2.5 7B"
        active_desc = "Local LLM via Ollama"
    
    return {
        "exam_sets_count": exam_sets_count,
        "questions_count": questions_count,
        "db_size_mb": round(db_size_mb, 2),
        "active_model": active_model,
        "active_desc": active_desc
    }

@app.get("/api/exam-sets")
def get_exam_sets():
    db_path = DB_PATH
    if not os.path.exists(db_path):
        return []
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source_file, chunk_title FROM documents ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    
    # Structure by source file
    sets_dict = {}
    for row in rows:
        qid, source_file, chunk_title = row
        if source_file not in sets_dict:
            sets_dict[source_file] = []
            
        p_num = len(sets_dict[source_file]) + 1
        sets_dict[source_file].append({
            "id": qid,
            "question_num": f"段落 {p_num}",
            "question_title": chunk_title
        })
        
    result = []
    for source_file, questions in sets_dict.items():
        result.append({
            "exam_set": source_file,
            "questions": questions
        })
        
    return result

@app.get("/api/question/{qid}")
def get_question(qid: int):
    db_path = DB_PATH
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database not initialized")
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source_file, chunk_title, content FROM documents WHERE id = ?", (qid,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document chunk not found")
        
    qid, source_file, chunk_title, content = row
    
    # Determine segment index for UI display
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM documents WHERE source_file = ? ORDER BY id", (source_file,))
    all_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    p_num = all_ids.index(qid) + 1 if qid in all_ids else 1
    
    return {
        "id": qid,
        "exam_set": source_file,
        "question_num": f"段落 {p_num}",
        "question_title": chunk_title,
        "original_question": f"來源檔案：{source_file}",
        "full_content": content
    }

@app.get("/api/search")
def search(q: str, top_k: int = 5):
    if not q:
        return []
    results = search_engine.search(q, top_k=top_k)
    
    formatted_results = []
    for r in results:
        doc = r["document"]
        formatted_results.append({
            "id": doc["id"],
            "exam_set": doc["source_file"],
            "question_num": "語意段落",
            "question_title": doc["chunk_title"],
            "original_question": f"來源檔案：{doc['source_file']}",
            "full_content": doc["content"],
            "score": r["score"],
            "type": r["type"]
        })
    return formatted_results

async def sse_chat_generator(message: str, history: List[Dict[str, str]], custom_api_key: str = None):
    # 1. Retrieve top-4 relevant chunks
    results = search_engine.search(message, top_k=4)
    
    citations = []
    context_parts = []
    for r in results:
        doc = r["document"]
        citations.append({
            "id": doc["id"],
            "exam_set": doc["source_file"],
            "question_num": f"段落",
            "question_title": doc["chunk_title"],
            "score": r["score"]
        })
        context_parts.append(
            f"來源手冊：{doc['source_file']}\n"
            f"章節標題：{doc['chunk_title']}\n"
            f"手冊內容：\n{doc['content']}"
        )
        
    # Yield citations as the first event
    yield f"event: citations\ndata: {json.dumps(citations, ensure_ascii=False)}\n\n"
    
    # 2. Construct prompt
    context_str = "\n\n====================\n\n".join(context_parts)
    prompt = (
        "你是一個專業的 AquaRAG 智慧水產養殖與系統架構學術專家 AI。請根據以下檢索到的相關技術指南與手冊內容作為參考，專業且有條理地回答使用者提出的問題。\n\n"
        "【檢索到的相關技術手冊內容】：\n"
        "------------------------------------\n"
        f"{context_str}\n"
        "------------------------------------\n\n"
        "【使用者提問】：\n"
        f"{message}\n\n"
        "【答題指引與要求】：\n"
        "1. 請提供專業、學術性強且條理分明的解答。請善用 Markdown 語法（粗體、列表、表格）來呈現。\n"
        "2. 如果檢索內容包含系統架構、機器學習模型微調、決定樹演算法、SQLite資料庫儲存、ESP32硬體整合或水產養殖實務等主題，請務必深入且具邏輯地融入你的回答中。\n"
        "3. 回答必須且只能使用「繁體中文」或「英文」（Traditional Chinese or English），絕對不要使用簡體中文或其他語言。\n"
        "4. 請不要在回答中重複複製整篇參考手冊內容，而是要進行融合與歸納整理，提供最切合使用者提問的解答。\n"
        "請開始答題："
    )
    
    # Check Gemini keys to try
    keys_to_try = []
    if custom_api_key and custom_api_key.strip():
        keys_to_try.append(custom_api_key.strip())
    elif os.getenv("GEMINI_API_KEY"):
        raw_keys = os.getenv("GEMINI_API_KEY").split(",")
        for k in raw_keys:
            k_clean = k.strip().strip('"').strip("'").strip()
            if k_clean:
                keys_to_try.append(k_clean)

    if keys_to_try:
        last_err = None
        for key in keys_to_try:
            try:
                from google.generativeai import client
                mgr = client._ClientManager()
                mgr.configure(api_key=key)
                
                model_id = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip().strip('"').strip("'")
                model = genai.GenerativeModel(model_id)
                model._client = mgr.get_default_client("generative")
                model._async_client = mgr.get_default_client("generative_async")
                
                # Format history for Gemini chat
                gemini_history = []
                for msg in history:
                    gemini_history.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [msg["content"]]
                    })
                
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        content_tw = zhconv.convert(chunk.text, "zh-tw")
                        payload_data = {"text": content_tw}
                        yield f"event: text\ndata: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
                
                yield "event: done\ndata: {}\n\n"
                return
            except Exception as e:
                last_err = e
                err_str = str(e)
                print(f"Gemini API attempt failed with key ending in ...{key[-6:] if len(key) > 6 else key}: {err_str}")
                continue
                
        err_data = {"error": f"Gemini API Error (All keys exhausted): {str(last_err)}"}
        yield f"event: error\ndata: {json.dumps(err_data, ensure_ascii=False)}\n\n"
        return

    # 3. Format history for Ollama chat
    ollama_messages = []
    for msg in history:
        ollama_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    # Add the current prompt
    ollama_messages.append({
        "role": "user",
        "content": prompt
    })
    
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    url = f"{ollama_host}/api/chat"
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5"),
        "messages": ollama_messages,
        "stream": True
    }
    
    # 4. Stream response
    try:
        response = requests.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        
        for chunk in response.iter_lines():
            if chunk:
                chunk_data = json.loads(chunk.decode("utf-8"))
                content = chunk_data.get("message", {}).get("content", "")
                if content:
                    content_tw = zhconv.convert(content, "zh-tw")
                    payload_data = {"text": content_tw}
                    yield f"event: text\ndata: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
                    
        yield "event: done\ndata: {}\n\n"
        
    except Exception as e:
        err_data = {"error": str(e)}
        yield f"event: error\ndata: {json.dumps(err_data, ensure_ascii=False)}\n\n"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
    return StreamingResponse(
        sse_chat_generator(request.message, history_dicts, custom_api_key=request.api_key),
        media_type="text/event-stream"
    )

# Serve static files
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>RAG Static UI is loading...</h1>")

app.mount("/static_multi", StaticFiles(directory=STATIC_DIR), name="static_multi")

def open_browser():
    webbrowser.open("http://localhost:8001/")

if __name__ == "__main__":
    if is_frozen:
        Timer(1.5, open_browser).start()
        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        uvicorn.run("app_multi:app", host="0.0.0.0", port=8001, reload=True)
