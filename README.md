# Natural Language to SQL Query Converter

A tool that converts natural language questions into executable SQL queries using an LLM API, enabling non-technical users to query a database directly through plain English.

## Architecture

```
Client (Next.js on Vercel) 
  ↓
FastAPI Backend (Docker on Render) 
  ↓
[Schema Loader | LLM Query Generator | Safety Validator | SQL Executor] 
  ↓
Database (PostgreSQL/MySQL/SQLite) 
  ↓
Results (JSON) → Client
```

## Tech Stack

- **Backend**: Python, FastAPI
- **LLM Integration**: OpenAI/Gemini/Claude API
- **Database**: PostgreSQL/MySQL/SQLite (configurable)
- **Query Safety**: sqlparse + custom validator
- **Frontend**: React (Next.js)
- **Backend Hosting**: Render (Docker)
- **Frontend Hosting**: Vercel

## Features

✅ Convert plain-English questions to SQL queries  
✅ Schema introspection and caching  
✅ Read-only mode by default (blocks DROP, DELETE, UPDATE, TRUNCATE)  
✅ Query validation and safety checks  
✅ Real-time query execution with results  
✅ Clear error handling  
✅ Query history tracking  

## Project Structure

```
nl-to-sql/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py      # API endpoints
│   │   ├── llm.py       # LLM integration
│   │   ├── safety.py    # Query validation
│   │   ├── executor.py  # SQL execution
│   │   └── schema.py    # Schema loader
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # Next.js application
│   ├── app/
│   ├── components/
│   └── package.json
└── README.md
```

## Environment Variables

### Backend (Render)
```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
LLM_API_KEY=your_api_key_here
LLM_PROVIDER=openai  # or gemini, claude
ALLOWED_ORIGINS=https://your-app.vercel.app
ENABLE_WRITE_MODE=false
PORT=8000
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_BASE_URL=https://your-app.onrender.com
```

## Local Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment

### Backend (Render)
1. Create new Web Service on Render
2. Connect GitHub repository
3. Select "Docker" as environment
4. Set environment variables in dashboard
5. Deploy (auto-deploys on push to main)

### Frontend (Vercel)
1. Import repository to Vercel
2. Framework preset: Next.js (auto-detected)
3. Set `NEXT_PUBLIC_API_BASE_URL` environment variable
4. Deploy (auto-deploys on push to main)

## API Endpoints

### `GET /health`
Health check endpoint

### `GET /schema`
Returns database schema (tables, columns, types)

### `POST /query`
Converts natural language to SQL and executes it

**Request Body:**
```json
{
  "question": "What were total sales last month?",
  "allow_write": false
}
```

**Response:**
```json
{
  "question": "What were total sales last month?",
  "sql": "SELECT SUM(amount) FROM sales WHERE...",
  "results": [...],
  "columns": [...],
  "row_count": 42
}
```

## Safety Features

- **Read-only by default**: Blocks DDL/DML operations
- **Query timeout**: Prevents long-running queries
- **Row limit**: Caps results at 100 rows
- **SQL injection protection**: Parameterized queries
- **Audit logging**: All queries logged with safety verdict

## Testing

Test the backend independently:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/schema
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me all orders"}'
```

## License

MIT
