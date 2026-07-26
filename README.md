# 🧠 Enterprise AI Knowledge Assistant

Ask questions in natural language and get answers directly from your company's PDF documents.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| LLM | Google Gemini 1.5 Flash / OpenAI GPT |
| RAG Framework | LangChain |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (local) |
| Vector DB | ChromaDB |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (Bearer tokens) |
| Deployment | Docker + Docker Compose |

## Architecture

```
User Question
     │
     ▼
FastAPI → JWT Auth
     │
     ▼
LangChain RAG Pipeline
     │
     ├── HuggingFace Embeddings (encode question)
     │
     ├── ChromaDB (retrieve top-5 relevant chunks)
     │
     └── Gemini/OpenAI LLM (generate grounded answer)
          │
          ▼
     Answer + Source Documents
```

## Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo>
cd enterprise-ai-assistant

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your Gemini or OpenAI API key
```

Get a free Gemini API key: https://aistudio.google.com/app/apikey

### 3. Run

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000

### 4. Docker (Alternative)

```bash
cp .env.example .env   # fill in your API key
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login → JWT token |
| GET | `/api/v1/auth/me` | Current user info |
| POST | `/api/v1/documents/upload` | Upload PDF |
| GET | `/api/v1/documents/` | List all documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/chat/ask` | Ask a question |
| GET | `/api/v1/chat/history` | Chat history |
| GET | `/health` | Health check |
| GET | `/stats` | Vector store stats |

Interactive docs: http://localhost:8000/docs

## Project Structure

```
enterprise-ai-assistant/
├── app/
│   ├── api/routes/          # FastAPI route handlers
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── documents.py
│   │   └── health.py
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   └── security.py      # JWT + password hashing
│   ├── db/
│   │   └── database.py      # SQLAlchemy async engine
│   ├── models/
│   │   └── models.py        # User, Document, ChatHistory ORM
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/
│   │   ├── rag_service.py   # Core RAG pipeline
│   │   ├── auth_service.py  # Auth business logic
│   │   ├── chat_service.py  # Q&A + history
│   │   └── document_service.py  # Upload + ingestion
│   └── main.py              # FastAPI app + lifespan
├── frontend/
│   └── index.html           # Single-page UI
├── uploads/                 # Uploaded PDFs (gitignored)
├── vectorstore/             # ChromaDB data (gitignored)
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Day 2 TODO (Deployment)

- [ ] Push to GitHub
- [ ] Deploy to Render/Railway
- [ ] Set environment variables in dashboard
- [ ] Test with real company documents
