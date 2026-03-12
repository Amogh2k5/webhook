# 🔍 GitHub Repo Tools

A collection of AI-powered developer tools built with FastAPI and Google Gemini. Includes a **GitHub Repository Q&A system** using RAG (Retrieval-Augmented Generation) and a **Commit Analyzer** that scores how meaningful a code change is.

---

## 🛠️ Projects

### 1. GitHub Repo Q&A (RAG)
Ask natural language questions about any GitHub repository. The system fetches all code files, chunks and embeds them into a vector database (ChromaDB), then uses Gemini to answer questions with file references and code snippets.

### 2. Commit Analyzer
Fetches the latest commit from a GitHub repo, extracts the old and new versions of changed files, and uses Gemini to score how meaningful the change is on a scale of 0–100. Ignores cosmetic changes like whitespace and formatting.

---

## 📁 Project Structure

```
webhook/
├── github_qa.py          # RAG-based GitHub repo Q&A (FastAPI)
├── compare_code.py       # Commit meaningfulness analyzer (FastAPI)
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

```bash
pip install PyGithub google-generativeai chromadb sentence-transformers fastapi uvicorn requests pydantic
```

### Run the Q&A server

```bash
python github_qa.py
# Docs: http://127.0.0.1:8000/docs
```

### Run the Commit Analyzer

```bash
uvicorn compare_code:app --host 127.0.0.1 --port 8001 --reload
# Docs: http://127.0.0.1:8001/docs
```

---

## 📡 API Endpoints

### GitHub Q&A (`port 8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`      | Health check & repo status |
| `POST` | `/ask`   | Ask a question about the repo |

**Example request:**
```json
POST /ask
{
  "question": "How does authentication work?",
  "n_context": 5
}
```

### Commit Analyzer (`port 8001`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/check_latest_commit` | Fetch latest commit and score its meaningfulness |
| `GET` | `/last_code` | Retrieve the old and new code from the last check |

**Example response:**
```json
{
  "status": "success",
  "file": "main.py",
  "meaningful_change": 72,
  "timestamp": "2025-03-12T10:00:00"
}
```

---

## ⚙️ Configuration

Set these variables at the top of each file before running:

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | Your GitHub personal access token |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `REPO_NAME` | Target repo in `owner/repo` format |

> ⚠️ **Never commit API keys or tokens to GitHub.** Move them to a `.env` file and use `python-dotenv` to load them.

---

## 🧠 How It Works

**Q&A (RAG pipeline):**
1. Fetches all text-based files from the GitHub repo
2. Splits files into overlapping chunks (1000 chars, 200 overlap)
3. Embeds chunks using `all-MiniLM-L6-v2` (SentenceTransformers)
4. Stores embeddings in ChromaDB (in-memory vector store)
5. On query: embeds the question, retrieves top-k similar chunks, sends to Gemini

**Commit Analyzer:**
1. Fetches the latest commit SHA via GitHub API
2. Retrieves old file content from the parent commit
3. Retrieves new file content from the latest commit
4. Sends both to Gemini with a scoring prompt
5. Returns a 0–100 meaningfulness score

---

## 🔮 Future Improvements

- [ ] Move API keys to `.env` file
- [ ] Support analyzing all changed files per commit (not just the first)
- [ ] Webhook endpoint so GitHub triggers the analyzer automatically on push
- [ ] Persistent ChromaDB storage across restarts
- [ ] Frontend UI for the Q&A system

---

## 👤 Author

**Amogh** — [github.com/Amogh2k5](https://github.com/Amogh2k5)
