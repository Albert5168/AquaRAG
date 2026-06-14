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

from search_engine import SearchEngine

# Detect if running in a PyInstaller bundle
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    is_frozen = True
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    is_frozen = False

def clean_model_name(model_id: str, default_model: str = "gemini-2.0-flash") -> str:
    if not model_id:
        return default_model
    model_id = model_id.strip().strip('"').strip("'")
    if (model_id.startswith("AIzaSy") or 
        model_id.startswith("AQ.") or 
        model_id.startswith("sk-or-") or 
        len(model_id) > 25):
        return default_model
    return model_id

# Resolve Database Path (writable in working directory if possible)
DB_PATH = os.path.join(os.getcwd(), "rag_database.db")
if not os.path.exists(DB_PATH):
    default_db_path = os.path.join(bundle_dir, "rag_database.db")
    if os.path.exists(default_db_path):
        try:
            shutil.copy(default_db_path, DB_PATH)
        except Exception as e:
            print(f"Error copying initial database to current working directory: {e}")
            # Fallback to the read-only bundled database path
            DB_PATH = default_db_path

# Resolve Static Directory Path
STATIC_DIR = os.path.join(bundle_dir, "static")

app = FastAPI(title="魚類生理學歷屆試題 RAG 系統")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Search Engine
search_engine = SearchEngine(db_path=DB_PATH, embed_model="nomic-embed-text")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
    api_key: str = None
    provider: str = None
    model: str = None

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
    
    cursor.execute("SELECT COUNT(DISTINCT exam_set) FROM questions")
    exam_sets_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    questions_count = cursor.fetchone()[0]
    
    conn.close()
    
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    
    if os.getenv("GEMINI_API_KEY"):
        model_id = clean_model_name(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
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
    cursor.execute("SELECT id, exam_set, question_num, question_title FROM questions ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    
    # Structure by exam set
    sets_dict = {}
    for row in rows:
        qid, exam_set, q_num, q_title = row
        if exam_set not in sets_dict:
            sets_dict[exam_set] = []
        sets_dict[exam_set].append({
            "id": qid,
            "question_num": q_num,
            "question_title": q_title
        })
        
    result = []
    for exam_set, questions in sets_dict.items():
        result.append({
            "exam_set": exam_set,
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
    cursor.execute("SELECT id, exam_set, question_num, question_title, original_question, full_content FROM questions WHERE id = ?", (qid,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
        
    qid, exam_set, q_num, q_title, orig_q, content = row
    return {
        "id": qid,
        "exam_set": exam_set,
        "question_num": q_num,
        "question_title": q_title,
        "original_question": orig_q,
        "full_content": content
    }

@app.get("/api/search")
def search(q: str, top_k: int = 5):
    if not q:
        return []
    results = search_engine.search(q, top_k=top_k)
    
    formatted_results = []
    for r in results:
        q_data = r["question"]
        formatted_results.append({
            "id": q_data["id"],
            "exam_set": q_data["exam_set"],
            "question_num": q_data["question_num"],
            "question_title": q_data["question_title"],
            "original_question": q_data["original_question"],
            "full_content": q_data["full_content"],
            "score": r["score"],
            "type": r["type"]
        })
    return formatted_results

async def sse_chat_generator(message: str, history: List[Dict[str, str]], custom_api_key: str = None, provider: str = None, model: str = None):
    # 1. Retrieve top-4 relevant chunks
    results = search_engine.search(message, top_k=4)
    
    citations = []
    context_parts = []
    for r in results:
        q = r["question"]
        citations.append({
            "id": q["id"],
            "exam_set": q["exam_set"],
            "question_num": q["question_num"],
            "question_title": q["question_title"],
            "score": r["score"]
        })
        context_parts.append(
            f"來源：{q['exam_set']} - {q['question_num']}\n"
            f"題目：{q['question_title']}\n"
            f"專家解答內容：\n{q['full_content']}"
        )
        
    # Yield citations as the first event
    yield f"event: citations\ndata: {json.dumps(citations, ensure_ascii=False)}\n\n"
    
    # 2. Construct prompt
    context_str = "\n\n====================\n\n".join(context_parts)
    prompt = (
        "你是一個「魚類生理學」的學術與國家考試輔導專家 AI。請根據以下檢索到的歷屆試題專家解答作為參考，專業且有條理地回答使用者提出的問題。\n\n"
        "【檢索到的相關歷屆試題與專家解答】：\n"
        "------------------------------------\n"
        f"{context_str}\n"
        "------------------------------------\n\n"
        "【使用者提問】：\n"
        f"{message}\n\n"
        "【答題指引與要求】：\n"
        "1. 請提供專業、學術性強且條理分明的解答。請善用 Markdown 語法（粗體、列表、表格）來呈現。\n"
        "2. 如果檢索內容包含生理機制（如滲透壓調節、呼吸作用、循環、內分泌、消化與吸收等）或水產養殖實務案例，請務必深入淺出地融入你的回答中。\n"
        "3. 回答必須且只能使用「繁體中文」或「英文」（Traditional Chinese or English），絕對不要使用簡體中文或其他語言。\n"
        "4. 請不要在回答中重複複製整篇參考解答，而是要進行融合與歸納整理，提供最切合使用者提問的解答。\n"
        "請開始答題："
    )
    
    # Check if this is OpenRouter provider
    is_openrouter = (provider == "openrouter") or (custom_api_key and custom_api_key.strip().startswith("sk-or-"))
    
    if is_openrouter:
        try:
            or_key = custom_api_key.strip() if (custom_api_key and custom_api_key.strip()) else os.getenv("OPENROUTER_API_KEY")
            if not or_key:
                raise Exception("Missing OpenRouter API Key. Please configure it in Settings.")
            
            or_model = model.strip() if (model and model.strip()) else os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-1.2b-instruct:free")
            
            or_messages = []
            for msg in history:
                or_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            or_messages.append({
                "role": "user",
                "content": prompt
            })
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aquarag.onrender.com",
                "X-Title": "AquaRAG"
            }
            payload = {
                "model": or_model,
                "messages": or_messages,
                "stream": True
            }
            
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            response.raise_for_status()
            
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode("utf-8").strip()
                    if chunk_str.startswith("data: "):
                        data_content = chunk_str[6:].strip()
                        if data_content == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_content)
                            text = data_json["choices"][0]["delta"].get("content", "")
                            if text:
                                content_tw = zhconv.convert(text, "zh-tw")
                                payload_data = {"text": content_tw}
                                yield f"event: text\ndata: {json.dumps(payload_data, ensure_ascii=False)}\n\n"
                        except:
                            pass
            
            yield "event: done\ndata: {}\n\n"
            return
        except Exception as e:
            err_data = {"error": f"OpenRouter API Error: {str(e)}"}
            yield f"event: error\ndata: {json.dumps(err_data, ensure_ascii=False)}\n\n"
            return

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
                
                model_id = clean_model_name(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
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
        sse_chat_generator(
            request.message,
            history_dicts,
            custom_api_key=request.api_key,
            provider=request.provider,
            model=request.model
        ),
        media_type="text/event-stream"
    )

# Serve static files
# Create static directory if not exists
os.makedirs(STATIC_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>RAG Static UI is loading...</h1>")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def open_browser():
    webbrowser.open("http://localhost:8000/")

if __name__ == "__main__":
    if is_frozen:
        Timer(1.5, open_browser).start()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
