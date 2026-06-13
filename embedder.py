import json
import sqlite3
import numpy as np
import requests
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

import time
import google.generativeai as genai

def get_embedding(text, model="nomic-embed-text"):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        retries = 6
        delay = 2.0
        for attempt in range(retries):
            try:
                genai.configure(api_key=gemini_key)
                response = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=text,
                    output_dimensionality=768
                )
                emb = response.get("embedding")
                if isinstance(emb, dict) and "values" in emb:
                    return emb["values"]
                elif isinstance(emb, list):
                    return emb
                else:
                    print(f"Error in Gemini embedding response: {response}")
                    return None
            except Exception as e:
                err_msg = str(e)
                if attempt < retries - 1:
                    print(f"Gemini API error (attempt {attempt+1}/{retries}). Retrying in {delay}s... Error: {e}")
                    time.sleep(delay)
                    delay *= 2
                else:
                    print(f"Failed to get Gemini embedding after {retries} attempts: {e}")
                    return None
        return None

    # Fallback to local Ollama
    url = "http://localhost:11434/api/embeddings"
    data = {
        "model": model,
        "prompt": text
    }
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        if "embedding" in res_json:
            return res_json["embedding"]
        else:
            print(f"Error in response: {res_json}")
            return None
    except Exception as e:
        print(f"Failed to get embedding for text: {text[:30]}... Error: {e}")
        return None

def init_db(db_path="rag_database.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create table for questions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        exam_set TEXT,
        question_num TEXT,
        question_title TEXT,
        original_question TEXT,
        full_content TEXT,
        embedding BLOB
    )
    """)
    conn.commit()
    return conn

def main():
    json_path = "parsed_questions.json"
    db_path = "rag_database.db"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Run parser.py first.")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    print(f"Loaded {len(questions)} questions from JSON.")
    
    conn = init_db(db_path)
    cursor = conn.cursor()
    
    # Check if there are already records
    cursor.execute("SELECT COUNT(*) FROM questions")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"Database already contains {existing_count} records.")
        # Ask to overwrite or continue? Since this is run non-interactively, we will overwrite by default
        print("Clearing existing records and re-indexing...")
        cursor.execute("DELETE FROM questions")
        conn.commit()
        
    indexed_count = 0
    
    for idx, q in enumerate(questions):
        print(f"Processing [{idx+1}/{len(questions)}]: {q['exam_set']} - {q['question_num']}")
        
        # We will embed the combination of the title, original question, and the first 1000 characters of the answer.
        # This provides a strong representation of both the question and the context of the answer.
        text_to_embed = f"考試科套：{q['exam_set']}\n題目：{q['question_title']}\n原題：{q['original_question']}\n專家解答：{q['full_content'][:1000]}"
        
        emb = get_embedding(text_to_embed)
        
        if emb is None:
            print(f"Skipping question {q['id']} due to embedding failure.")
            continue
            
        # Convert embedding float list to binary BLOB
        emb_arr = np.array(emb, dtype=np.float32)
        emb_blob = emb_arr.tobytes()
        
        cursor.execute("""
        INSERT INTO questions (id, exam_set, question_num, question_title, original_question, full_content, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (q['id'], q['exam_set'], q['question_num'], q['question_title'], q['original_question'], q['full_content'], emb_blob))
        
        indexed_count += 1
        
        # Commit every 10 records
        if indexed_count % 10 == 0:
            conn.commit()
            
    conn.commit()
    conn.close()
    
    print(f"Successfully indexed {indexed_count} questions into {db_path}!")

if __name__ == "__main__":
    main()
