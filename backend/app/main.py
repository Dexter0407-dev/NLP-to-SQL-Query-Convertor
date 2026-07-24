"""
FastAPI application — Natural Language to SQL Query Converter
Modules: Schema Loader | LLM Query Generator | Safety Validator | SQL Executor
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.executor import execute_query
from app.llm import generate_sql
from app.models import (
    ErrorResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SchemaResponse,
)
from app.safety import inject_row_limit, validate_query
from app.schema import load_schema
from app.uploader import load_csv_to_db

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Seed demo DB on startup if using SQLite and no DB file exists ─────────────
def _maybe_seed_demo_db() -> None:
    url = settings.database_url
    if not (url.startswith("sqlite") and url != "sqlite:///:memory:"):
        return
    db_path = url.replace("sqlite:///", "").replace("sqlite://", "") or "./sample.db"
    if not os.path.exists(db_path):
        logger.info("Sample DB not found — seeding demo data at %s", db_path)
        try:
            from app.seed import seed
            seed()
        except Exception as exc:
            logger.warning("Could not seed demo DB: %s", exc)


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="NL to SQL API",
    description="Convert natural language questions to executable SQL queries.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    _maybe_seed_demo_db()
    # Warm up schema cache
    try:
        load_schema()
        logger.info("Schema cache warmed up on startup.")
    except Exception as exc:
        logger.warning("Could not warm up schema cache: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Liveness probe — returns 200 when the service is up."""
    return HealthResponse(
        status="ok",
        database=settings.database_url.split("://")[0],
        llm_provider=settings.llm_provider,
    )


@app.get(
    "/schema",
    response_model=SchemaResponse,
    tags=["Schema"],
    summary="Introspect the database schema",
)
async def get_schema(refresh: bool = Query(False, description="Force cache refresh")) -> SchemaResponse:
    """
    Returns all table names, column names, and data types for the connected database.
    Results are cached in memory. Pass ?refresh=true to bust the cache.
    """
    try:
        return load_schema(force_refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post(
    "/query",
    response_model=QueryResponse,
    tags=["Query"],
    summary="Convert a natural language question to SQL and execute it",
    responses={
        400: {"model": ErrorResponse, "description": "Unsafe query or bad input"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "LLM or database unavailable"},
    },
)
async def run_query(body: QueryRequest) -> QueryResponse:
    """
    1. Load schema (from cache)
    2. Call LLM to generate SQL
    3. Validate query for safety
    4. Inject row limit
    5. Execute and return results
    """
    # Step 1 — Load schema
    try:
        schema = load_schema()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Step 2 — Generate SQL via LLM
    try:
        sql = generate_sql(body.question, schema)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Step 3 — Safety validation
    safety = validate_query(sql, allow_write=body.allow_write)
    if not safety.safe:
        raise HTTPException(
            status_code=400,
            detail=safety.reason or "Query blocked by safety validator.",
        )

    # Step 4 — Inject row limit (read-only queries only)
    if not body.allow_write:
        sql = inject_row_limit(sql)

    # Step 5 — Execute
    try:
        columns, results = execute_query(sql)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return QueryResponse(
        question=body.question,
        sql=sql,
        columns=columns,
        results=results,
        row_count=len(results),
        safe=True,
    )


@app.post(
    "/upload",
    tags=["Upload"],
    summary="Upload a CSV file and query it with natural language",
)
async def upload_csv(file: UploadFile = File(...)) -> dict:
    """
    Accepts a CSV file, loads it into SQLite as a table,
    refreshes the schema cache, and returns the new table info.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    try:
        result = load_csv_to_db(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("CSV upload failed")
        raise HTTPException(status_code=500, detail=f"Failed to load CSV: {exc}")

    return result


@app.post(
    "/upload",
    tags=["Upload"],
    summary="Upload a CSV file and query it with natural language",
)
async def upload_csv(file: UploadFile = File(...)) -> dict:
    """
    Accepts a CSV file, loads it into SQLite as a table,
    refreshes the schema cache, and returns the new table info.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    try:
        result = load_csv_to_db(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("CSV upload failed")
        raise HTTPException(status_code=500, detail=f"Failed to load CSV: {exc}")

    return result


@app.get(
    "/preview/{table_name}",
    tags=["Preview"],
    summary="Preview rows from a table",
)
async def preview_table(table_name: str, limit: int = Query(100, ge=1, le=1000)) -> dict:
    """
    Returns up to `limit` rows from the given table so the frontend
    can render a data preview.
    """
    import re
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        raise HTTPException(status_code=400, detail="Invalid table name.")
    try:
        columns, results = execute_query(f'SELECT * FROM "{table_name}" LIMIT {limit};')
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"table_name": table_name, "columns": columns, "results": results, "row_count": len(results)}
