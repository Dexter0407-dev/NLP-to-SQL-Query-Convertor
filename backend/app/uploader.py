"""
CSV Upload Module
Receives a CSV file, loads it into the active SQLite DB as a table,
and refreshes the schema cache.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import sqlite3

from app.config import settings
from app.schema import load_schema

logger = logging.getLogger(__name__)


def _sanitize_name(name: str) -> str:
    """Convert a header/filename string to a safe SQL identifier."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "col"


def _infer_type(values: list[str]) -> str:
    """Infer SQLite column type from a sample of string values."""
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "TEXT"
    # Try INTEGER
    try:
        all(int(v) for v in non_empty)
        return "INTEGER"
    except ValueError:
        pass
    # Try REAL
    try:
        all(float(v) for v in non_empty)
        return "REAL"
    except ValueError:
        pass
    return "TEXT"


def _get_db_path() -> str:
    url = settings.database_url
    return url.replace("sqlite:///", "").replace("sqlite://", "") or "./sample.db"


def load_csv_to_db(filename: str, content: bytes) -> dict:
    """
    Parse CSV bytes and load them into SQLite as a new table.
    Drops the table first if it already exists.
    Returns { table_name, row_count, columns }.
    """
    # Derive table name from filename (strip .csv)
    base = filename.rsplit(".", 1)[0]
    table_name = _sanitize_name(base) or "uploaded_data"

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV has no headers — make sure the first row contains column names.")

    raw_headers = list(reader.fieldnames)
    safe_headers = [_sanitize_name(h) for h in raw_headers]

    # Deduplicate header names
    seen: dict[str, int] = {}
    deduped: list[str] = []
    for h in safe_headers:
        if h in seen:
            seen[h] += 1
            deduped.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            deduped.append(h)
    safe_headers = deduped

    rows = [list(row.values()) for row in reader]
    if not rows:
        raise ValueError("CSV file is empty — no data rows found.")

    # Infer column types from first 50 rows
    sample = rows[:50]
    col_types = [
        _infer_type([r[i] if i < len(r) else "" for r in sample])
        for i in range(len(safe_headers))
    ]

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop + recreate table
    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
    col_defs = ", ".join(
        f'"{h}" {t}' for h, t in zip(safe_headers, col_types)
    )
    cursor.execute(f'CREATE TABLE "{table_name}" ({col_defs});')

    # Insert rows
    placeholders = ", ".join("?" * len(safe_headers))
    def coerce(val: str, typ: str) -> object:
        val = val.strip()
        if not val:
            return None
        if typ == "INTEGER":
            try: return int(val)
            except ValueError: return None
        if typ == "REAL":
            try: return float(val)
            except ValueError: return None
        return val

    clean_rows = [
        [coerce(r[i] if i < len(r) else "", col_types[i]) for i in range(len(safe_headers))]
        for r in rows
    ]
    cursor.executemany(
        f'INSERT INTO "{table_name}" VALUES ({placeholders})',
        clean_rows,
    )
    conn.commit()
    conn.close()

    logger.info("Loaded CSV '%s' → table '%s' (%d rows)", filename, table_name, len(rows))

    # Bust the schema cache so /schema returns fresh data
    load_schema(force_refresh=True)

    return {
        "table_name": table_name,
        "row_count": len(rows),
        "columns": [{"name": h, "type": t} for h, t in zip(safe_headers, col_types)],
    }
