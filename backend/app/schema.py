"""
Module 1 — Schema Loader
Introspects the connected database and returns table names, columns, and types.
Schema is cached in memory to avoid re-querying the DB on every request.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from app.config import settings
from app.models import ColumnInfo, SchemaResponse, TableInfo

logger = logging.getLogger(__name__)

_schema_cache: SchemaResponse | None = None


def _detect_db_type(url: str) -> str:
    if url.startswith("postgresql") or url.startswith("postgres"):
        return "postgresql"
    if url.startswith("mysql"):
        return "mysql"
    return "sqlite"


def _get_sqlite_schema(url: str) -> SchemaResponse:
    import sqlite3
    # Strip the sqlite:/// prefix
    db_path = url.replace("sqlite:///", "").replace("sqlite://", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    table_names = [r[0] for r in cursor.fetchall()]

    tables: List[TableInfo] = []
    for tname in table_names:
        cursor.execute(f"PRAGMA table_info('{tname}');")
        cols = [
            ColumnInfo(
                name=row[1],
                type=row[2] or "TEXT",
                nullable=not row[3],
            )
            for row in cursor.fetchall()
        ]
        cursor.execute(f"SELECT COUNT(*) FROM \"{tname}\";")
        row_count = cursor.fetchone()[0]
        tables.append(TableInfo(name=tname, columns=cols, row_count=row_count))

    conn.close()
    return SchemaResponse(tables=tables, database_type="sqlite")


def _get_postgres_schema(url: str) -> SchemaResponse:
    import psycopg2

    conn = psycopg2.connect(url)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    table_names = [r[0] for r in cursor.fetchall()]

    tables: List[TableInfo] = []
    for tname in table_names:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position;
        """, (tname,))
        cols = [
            ColumnInfo(name=r[0], type=r[1], nullable=(r[2] == "YES"))
            for r in cursor.fetchall()
        ]
        cursor.execute(f'SELECT COUNT(*) FROM "{tname}";')
        row_count = cursor.fetchone()[0]
        tables.append(TableInfo(name=tname, columns=cols, row_count=row_count))

    conn.close()
    return SchemaResponse(tables=tables, database_type="postgresql")


def _get_mysql_schema(url: str) -> SchemaResponse:
    import pymysql

    # pymysql expects host/user/pass/db from URL
    # e.g. mysql://user:pass@host:3306/dbname
    import re
    m = re.match(r"mysql\+?pymysql?://(.+):(.+)@(.+):(\d+)/(.+)", url)
    if not m:
        raise ValueError("Invalid MySQL connection URL")
    user, password, host, port, database = m.groups()

    conn = pymysql.connect(host=host, user=user, password=password,
                           database=database, port=int(port))
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES;")
    table_names = [r[0] for r in cursor.fetchall()]

    tables: List[TableInfo] = []
    for tname in table_names:
        cursor.execute(f"DESCRIBE `{tname}`;")
        cols = [
            ColumnInfo(name=r[0], type=r[1], nullable=(r[2] == "YES"))
            for r in cursor.fetchall()
        ]
        cursor.execute(f"SELECT COUNT(*) FROM `{tname}`;")
        row_count = cursor.fetchone()[0]
        tables.append(TableInfo(name=tname, columns=cols, row_count=row_count))

    conn.close()
    return SchemaResponse(tables=tables, database_type="mysql")


def load_schema(force_refresh: bool = False) -> SchemaResponse:
    """
    Load and cache the database schema.
    Pass force_refresh=True to bust the in-memory cache.
    """
    global _schema_cache

    if _schema_cache is not None and not force_refresh:
        return _schema_cache

    url = settings.database_url
    db_type = _detect_db_type(url)
    logger.info("Loading schema for database type: %s", db_type)

    try:
        if db_type == "sqlite":
            schema = _get_sqlite_schema(url)
        elif db_type == "postgresql":
            schema = _get_postgres_schema(url)
        elif db_type == "mysql":
            schema = _get_mysql_schema(url)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    except Exception as exc:
        logger.exception("Failed to load schema")
        raise RuntimeError(f"Could not introspect database schema: {exc}") from exc

    _schema_cache = schema
    logger.info("Schema loaded: %d table(s)", len(schema.tables))
    return schema


def schema_as_prompt_text(schema: SchemaResponse) -> str:
    """
    Render the schema into a compact text representation
    suitable for inclusion in an LLM prompt.
    """
    lines = [f"Database type: {schema.database_type}", ""]
    for table in schema.tables:
        col_parts = ", ".join(
            f"{c.name} {c.type}{'?' if c.nullable else ''}"
            for c in table.columns
        )
        lines.append(f"Table: {table.name} ({col_parts})")
    return "\n".join(lines)
