"""
Module 4 — SQL Execution & Results
Executes validated SQL queries against the target database
and returns results as JSON (rows + column headers).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)


def _detect_db_type(url: str) -> str:
    if url.startswith("postgresql") or url.startswith("postgres"):
        return "postgresql"
    if url.startswith("mysql"):
        return "mysql"
    return "sqlite"


def _execute_sqlite(sql: str) -> tuple[List[str], List[Dict[str, Any]]]:
    import sqlite3
    db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
    conn = sqlite3.connect(db_path, timeout=settings.query_timeout)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    conn.close()

    results = [dict(row) for row in rows]
    return columns, results


def _execute_postgres(sql: str) -> tuple[List[str], List[Dict[str, Any]]]:
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(settings.database_url, connect_timeout=settings.query_timeout)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc.name for desc in cursor.description] if cursor.description else []
    conn.close()

    results = [dict(row) for row in rows]
    return columns, results


def _execute_mysql(sql: str) -> tuple[List[str], List[Dict[str, Any]]]:
    import pymysql
    import re
    m = re.match(r"mysql\+?pymysql?://(.+):(.+)@(.+):(\d+)/(.+)", settings.database_url)
    if not m:
        raise ValueError("Invalid MySQL connection URL")
    user, password, host, port, database = m.groups()

    conn = pymysql.connect(
        host=host, user=user, password=password,
        database=database, port=int(port),
        connect_timeout=settings.query_timeout,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    conn.close()

    return columns, rows


def execute_query(sql: str) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Execute a SQL query and return (columns, results).
    Raises RuntimeError on execution errors with a readable message.
    """
    db_type = _detect_db_type(settings.database_url)
    logger.info("Executing query against %s: %s", db_type, sql.replace("\n", " "))

    try:
        if db_type == "sqlite":
            return _execute_sqlite(sql)
        elif db_type == "postgresql":
            return _execute_postgres(sql)
        elif db_type == "mysql":
            return _execute_mysql(sql)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    except Exception as exc:
        logger.exception("Query execution failed")
        # Extract user-friendly message
        msg = str(exc)
        # Remove raw tracebacks if present
        if "\n" in msg:
            msg = msg.split("\n")[0]
        raise RuntimeError(f"Query execution failed: {msg}") from exc
