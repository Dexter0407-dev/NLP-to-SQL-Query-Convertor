# 🗄️ Natural Language to SQL Query Converter

> Ask questions in plain English — get instant SQL queries and results from your data.

[![Backend CI](https://github.com/Dexter0407-dev/NLP-to-SQL-Query-Convertor/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/Dexter0407-dev/NLP-to-SQL-Query-Convertor/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/Dexter0407-dev/NLP-to-SQL-Query-Convertor/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/Dexter0407-dev/NLP-to-SQL-Query-Convertor/actions/workflows/frontend-ci.yml)

---

## 🚀 Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | https://nlp-to-sql-query-convertor.vercel.app |
| **Backend API** | https://nl-to-sql-backend-9owt.onrender.com |
| **API Docs** | https://nl-to-sql-backend-9owt.onrender.com/docs |

> ⚠️ Render free tier spins down after inactivity — the first request may take ~30 seconds to wake up.

---

## 📌 What It Does

- Type a plain-English question like *"What were total sales last month?"*
- The backend sends it to an LLM (Mistral AI) along with your database schema
- The LLM generates a SQL query
- The query is safety-validated (no DROP/DELETE/UPDATE allowed)
- Executed against the database and results are returned as a table

---

## 🏗️ Architecture

```
User (Browser)
    ↓
Next.js Frontend (Vercel)
    ↓  HTTPS
FastAPI Backend (Render / Docker)
    ↓
┌─────────────────────────────────────┐
│  Schema Loader  →  Cache            │
│  LLM Generator  →  Mistral AI API   │
│  Safety Validator (sqlparse)        │
│  SQL Executor                       │
└─────────────────────────────────────┘
    ↓
SQLite / PostgreSQL / MySQL
    ↓
JSON Results → Frontend Table
```

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, TypeScript |
| Backend | Python, FastAPI |
| LLM | Mistral AI (`mistral-small-latest`) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Safety | sqlparse + custom validator |
| Backend Hosting | Render (Docker) |
| Frontend Hosting | Vercel |
| CI/CD | GitHub Actions |

---

## 📁 Project Structure

```
NLP-to-SQL/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app + all endpoints
│   │   ├── llm.py         # LLM provider integrations
│   │   ├── safety.py      # SQL safety validator
│   │   ├── executor.py    # SQL execution engine
│   │   ├── schema.py      # DB schema loader + cache
│   │   ├── uploader.py    # CSV upload → SQLite
│   │   ├── seed.py        # Sample data seeder
│   │   ├── models.py      # Pydantic schemas
│   │   └── config.py      # Environment settings
│   ├── tests/
│   │   └── test_api.py    # Smoke tests (8 tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   └── Dashboard.tsx  # Main UI component
│   ├── vercel.json
│   └── package.json
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
├── render.yaml
└── README.md
```

---

## ✨ Features

- 💬 **Natural language queries** — ask anything in plain English
- 📊 **Data preview** — see your full dataset as a table instantly
- 📁 **CSV upload** — drag & drop any CSV, auto-detects column types
- 🔒 **Read-only safety** — blocks DROP, DELETE, UPDATE, TRUNCATE by default
- 🧠 **Schema-aware** — LLM always sees real column names, no hallucinations
- 📄 **SQL transparency** — generated SQL shown before results
- 📑 **Pagination** — handles large result sets cleanly
- 🗂️ **Multi-table** — switch between uploaded datasets
- 🔄 **Query history** — re-run recent questions with one click

---

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- A free [Mistral AI](https://console.mistral.ai) API key

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Run
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# Run
npm run dev
```

Frontend runs at: http://localhost:3000

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./sample.db` |
| `LLM_PROVIDER` | LLM provider to use | `mistral` |
| `LLM_API_KEY` | Your LLM API key | `HAIj...` |
| `LLM_MODEL` | Model name (optional) | `mistral-small-latest` |
| `ENABLE_WRITE_MODE` | Allow write SQL ops | `false` |
| `ROW_LIMIT` | Max rows returned | `100` |
| `QUERY_TIMEOUT` | Query timeout seconds | `30` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `https://your-app.vercel.app` |

### Frontend (Vercel Environment Variables)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | `https://nl-to-sql-backend-9owt.onrender.com` |

---

## 🌐 Deployment

### Backend → Render

1. Go to [render.com](https://render.com) → **New Web Service**
2. Connect GitHub repo → select this repository
3. **Root Directory**: `backend`
4. **Environment**: `Docker`
5. Add environment variables (see table above)
6. Deploy — auto-deploys on every push to `main`

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import this repository
3. **Root Directory**: `frontend`
4. Add `NEXT_PUBLIC_API_BASE_URL` env variable
5. Deploy — auto-deploys on every push to `main`

---

## 🔁 CI/CD

GitHub Actions runs automatically on every push to `main`:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `backend-ci.yml` | Changes in `backend/` | Runs 8 pytest smoke tests on Python 3.11 & 3.12 |
| `frontend-ci.yml` | Changes in `frontend/` | TypeScript check + Next.js build on Node 20 & 22 |

---

## 📡 API Reference

### `GET /health`
```json
{ "status": "ok", "database": "sqlite", "llm_provider": "mistral" }
```

### `GET /schema`
Returns all tables, columns and types from the connected database.

### `GET /preview/{table_name}?limit=100`
Returns up to `limit` rows from a table for data preview.

### `POST /query`
```json
// Request
{ "question": "What is the total revenue?", "allow_write": false }

// Response
{
  "question": "What is the total revenue?",
  "sql": "SELECT SUM(price * quantity) AS total_revenue FROM orders LIMIT 100;",
  "columns": ["total_revenue"],
  "results": [{ "total_revenue": 48579.25 }],
  "row_count": 1,
  "safe": true
}
```

### `POST /upload`
Accepts a CSV file (multipart/form-data), loads it as a SQLite table.
```json
// Response
{ "table_name": "customers", "row_count": 100, "columns": [...] }
```

---

## 🔒 Security

- Destructive SQL (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`) blocked by default
- All queries capped at 100 rows to prevent runaway queries
- Secrets loaded from environment variables — never committed to source
- CORS restricted to configured frontend origins in production

---

## 📝 License

MIT — feel free to use, modify and deploy.

---

Built with ❤️ using FastAPI, Next.js, and Mistral AI
