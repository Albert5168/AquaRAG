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

class MultiSearchEngine:
    def __init__(self, db_path="multi_knowledge.db", embed_model="nomic-embed-text"):
        self.db_path = db_path
        self.embed_model = embed_model
        self.documents = []
        self.embeddings = []
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.db_path):
            print(f"Warning: Database {self.db_path} does not exist yet.")
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, source_file, chunk_title, content, embedding FROM documents")
            rows = cursor.fetchall()
            
            self.documents = []
            emb_list = []
            
            for row in rows:
                doc_id, source_file, chunk_title, content, emb_bytes = row
                emb = np.frombuffer(emb_bytes, dtype=np.float32)
                
                self.documents.append({
                    "id": doc_id,
                    "source_file": source_file,
                    "chunk_title": chunk_title,
                    "content": content
                })
                emb_list.append(emb)
                
            if emb_list:
                self.embeddings = np.vstack(emb_list)
                print(f"MultiSearchEngine loaded {len(self.documents)} chunks with embedding matrix shape {self.embeddings.shape}.")
            else:
                self.embeddings = np.array([])
                print("MultiSearchEngine loaded 0 chunks.")
        except sqlite3.OperationalError as e:
            print(f"Database table error: {e}. Run multi_embedder.py first.")
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
        if len(self.documents) == 0:
            return []
            
        # Try semantic search
        query_emb = self.get_query_embedding(query)
        if query_emb is None or self.embeddings.size == 0:
            print("Falling back to keyword search...")
            return self.keyword_search(query, top_k)
            
        # Cosine similarity calculation
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
                "document": self.documents[idx],
                "score": score,
                "type": "semantic"
            })
            
        return results

    def keyword_search(self, query, top_k=5):
        results = []
        query_words = query.lower().split()
        
        for doc in self.documents:
            score = 0
            content_lower = doc["content"].lower()
            title_lower = doc["chunk_title"].lower()
            source_lower = doc["source_file"].lower()
            
            for word in query_words:
                if word in title_lower:
                    score += 5.0
                elif word in source_lower:
                    score += 3.0
                elif word in content_lower:
                    score += 1.0
                    
            if score > 0:
                results.append((doc, score))
                
        results.sort(key=lambda x: x[1], reverse=True)
        
        max_score = results[0][1] if results else 1.0
        return [{
            "document": item[0],
            "score": min(0.95, item[1] / max_score * 0.8),
            "type": "keyword"
        } for item in results[:top_k]]

if __name__ == "__main__":
    # Test search engine if run directly
    se = MultiSearchEngine()
    if se.documents:
        res = se.search("LLM", top_k=2)
        print("Test Search Results:")
        for r in res:
            print(f"Score: {r['score']:.4f} | {r['document']['source_file']} - {r['document']['chunk_title']}")
            print(f"Content: {r['document']['content'][:100]}...")
            print("-" * 50)
