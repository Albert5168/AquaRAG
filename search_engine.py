import sqlite3
import numpy as np
import requests
import os
import google.generativeai as genai

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

class SearchEngine:
    def __init__(self, db_path="rag_database.db", embed_model="nomic-embed-text"):
        self.db_path = db_path
        self.embed_model = embed_model
        self.questions = []
        self.embeddings = []
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.db_path):
            print(f"Warning: Database {self.db_path} does not exist yet.")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, exam_set, question_num, question_title, original_question, full_content, embedding FROM questions")
            rows = cursor.fetchall()
            
            self.questions = []
            emb_list = []
            
            for row in rows:
                qid, exam_set, q_num, q_title, orig_q, content, emb_bytes = row
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                
                self.questions.append({
                    "id": qid,
                    "exam_set": exam_set,
                    "question_num": q_num,
                    "question_title": q_title,
                    "original_question": orig_q,
                    "full_content": content
                })
                emb_list.append(emb)
                
            if emb_list:
                self.embeddings = np.vstack(emb_list)
                print(f"SearchEngine loaded {len(self.questions)} questions with embedding matrix shape {self.embeddings.shape}.")
            else:
                self.embeddings = np.array([])
                print("SearchEngine loaded 0 questions.")
        except sqlite3.OperationalError as e:
            print(f"Database table error: {e}. Run embedder.py first.")
        finally:
            conn.close()

    def reload(self):
        self.load_database()

    def get_query_embedding(self, query):
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                response = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=query,
                    output_dimensionality=768
                )
                emb = response.get("embedding")
                if isinstance(emb, dict) and "values" in emb:
                    return np.array(emb["values"], dtype=np.float32)
                elif isinstance(emb, list):
                    return np.array(emb, dtype=np.float32)
                else:
                    print(f"Error in Gemini embedding query response: {response}")
                    return None
            except Exception as e:
                print(f"Error embedding query via Gemini: {e}")
                return None

        # Fallback to local Ollama
        url = "http://localhost:11434/api/embeddings"
        data = {
            "model": self.embed_model,
            "prompt": query
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return np.array(response.json()["embedding"], dtype=np.float32)
        except Exception as e:
            print(f"Error embedding query: {e}")
            return None

    def search(self, query, top_k=5):
        if len(self.questions) == 0:
            return []
            
        # Try semantic search
        query_emb = self.get_query_embedding(query)
        if query_emb is None or self.embeddings.size == 0:
            print("Falling back to keyword search...")
            return self.keyword_search(query, top_k)
            
        # Cosine similarity calculation
        # query_emb shape: (dim,)
        # embeddings shape: (N, dim)
        dot_product = np.dot(self.embeddings, query_emb)
        norm_a = np.linalg.norm(self.embeddings, axis=1)
        norm_b = np.linalg.norm(query_emb)
        
        similarities = dot_product / (norm_a * norm_b + 1e-8)
        
        # Get top K indices sorted in descending order of similarity
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            results.append({
                "question": self.questions[idx],
                "score": score,
                "type": "semantic"
            })
            
        return results

    def keyword_search(self, query, top_k=5):
        results = []
        query_words = query.lower().split()
        
        for q in self.questions:
            score = 0
            content_lower = q["full_content"].lower()
            title_lower = q["question_title"].lower()
            
            for word in query_words:
                if word in title_lower:
                    score += 5.0
                elif word in content_lower:
                    score += 1.0
                    
            if score > 0:
                results.append((q, score))
                
        results.sort(key=lambda x: x[1], reverse=True)
        
        max_score = results[0][1] if results else 1.0
        return [{
            "question": item[0],
            "score": min(0.95, item[1] / max_score * 0.8),
            "type": "keyword"
        } for item in results[:top_k]]

if __name__ == "__main__":
    # Test search engine if run directly
    se = SearchEngine()
    if se.questions:
        res = se.search("呼吸生理與循環系統", top_k=2)
        print("Test Search Results:")
        for r in res:
            print(f"Score: {r['score']:.4f} | {r['question']['exam_set']} - {r['question']['question_num']}")
            print(f"Title: {r['question']['question_title']}")
            print("-" * 50)
