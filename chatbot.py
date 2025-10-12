"""
FastAPI GitHub Repository Q&A with RAG
pip install PyGithub google-generativeai chromadb sentence-transformers fastapi uvicorn
"""

import base64
from github import Github
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Configuration
GITHUB_TOKEN = "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"
GEMINI_API_KEY = "AIzaSyCyAf0B1uWmngRjDVeE-HmqAPqgLivrSG8"
REPO_NAME = "adityaatre26/Cokaam"

class GitHubQA:
    def __init__(self, github_token: str, gemini_key: str):
        self.github = Github(github_token)
        genai.configure(api_key=gemini_key)
        self.model = genai.GenerativeModel('gemini-pro-latest')
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        client = chromadb.Client(Settings(anonymized_telemetry=False, allow_reset=True))
        try: client.delete_collection("repo")
        except: pass
        self.collection = client.create_collection("repo", metadata={"hnsw:space": "cosine"})
        
        self.repo_name = None
        self.is_ready = False
        
    def extract_repo(self, repo_name: str):
        print(f"Extracting: {repo_name}")
        self.repo_name = repo_name
        repo = self.github.get_repo(repo_name)
        
        docs, metas, ids = [], [], []
        file_id = 0
        contents = repo.get_contents("")
        
        text_exts = {'py','js','jsx','ts','tsx','java','cpp','c','h','cs','rb','go','rs',
                     'php','html','css','json','xml','yaml','yml','md','txt','sh','sql'}
        
        while contents:
            fc = contents.pop(0)
            if fc.type == "dir":
                contents.extend(repo.get_contents(fc.path))
            elif fc.size < 500000:
                ext = fc.name.split('.')[-1].lower() if '.' in fc.name else ''
                if ext in text_exts or fc.name in ['Dockerfile','Makefile','README']:
                    try:
                        content = base64.b64decode(fc.content).decode('utf-8')
                        chunks = self._chunk(content, fc.path)
                        
                        for i, chunk in enumerate(chunks):
                            docs.append(chunk)
                            metas.append({'file_path': fc.path, 'chunk': i})
                            ids.append(f"f{file_id}_c{i}")
                        
                        file_id += 1
                        print(f"✓ {fc.path}")
                    except: pass
        
        if docs:
            embeddings = self.embedder.encode(docs, show_progress_bar=True).tolist()
            self.collection.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)
            self.is_ready = True
        
        print(f"Done! Files: {file_id}, Chunks: {len(docs)}")
        return {'files': file_id, 'chunks': len(docs)}
    
    def _chunk(self, text: str, path: str, size: int = 1000, overlap: int = 200):
        header = f"File: {path}\n\n"
        if len(text) <= size:
            return [header + text]
        
        chunks, start = [], 0
        while start < len(text):
            end = start + size
            if end < len(text):
                nl = text.rfind('\n', start, end)
                if nl > start + size // 2:
                    end = nl
            chunks.append(header + text[start:end])
            start = end - overlap if end < len(text) else end
        return chunks
    
    def ask(self, question: str, n: int = 5):
        if not self.is_ready:
            return "System not ready"
        
        qemb = self.embedder.encode([question])[0].tolist()
        results = self.collection.query(query_embeddings=[qemb], n_results=min(n, self.collection.count()))
        
        context = "\n".join([f"--- {m['file_path']} ---\n{d}\n" 
                            for d, m in zip(results['documents'][0], results['metadatas'][0])])
        
        prompt = f"""Analyze GitHub repo: {self.repo_name}

Context:
{context}

Question: {question}

Provide concise answer with file references and code snippets."""

        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            return f"Error: {e}"

# FastAPI Setup
app = FastAPI(title="GitHub Repo Q&A", version="1.0")
qa: Optional[GitHubQA] = None

class Question(BaseModel):
    question: str = Field(..., min_length=1)
    n_context: int = Field(5, ge=1, le=20)

class Answer(BaseModel):
    question: str
    answer: str
    repo: str

@app.on_event("startup")
async def startup():
    global qa
    print("Initializing...")
    qa = GitHubQA(GITHUB_TOKEN, GEMINI_API_KEY)
    qa.extract_repo(REPO_NAME)
    print("Ready!")

@app.get("/")
async def root():
    return {
        "service": "GitHub Repo Q&A",
        "repo": REPO_NAME,
        "status": "ready" if qa and qa.is_ready else "initializing"
    }

@app.post("/ask", response_model=Answer)
async def ask(q: Question):
    if not qa or not qa.is_ready:
        raise HTTPException(503, "System initializing")
    
    answer = qa.ask(q.question, q.n_context)
    return Answer(question=q.question, answer=answer, repo=qa.repo_name)

if __name__ == "__main__":
    print("Starting server...\n Docs: http://127.0.0.1:8000/docs\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)