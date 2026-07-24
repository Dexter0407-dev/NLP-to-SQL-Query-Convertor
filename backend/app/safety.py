"""
Module 3 — Query Safety Validation
Blocks DDL/DML statements unless write mode is explicitly enabled.
Enforces row-limit caps and logs every query with its safety verdict.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DDL, DML

from app.config import settings

logger = logging.getLogger(__name__)

# Statements that mutate or destroy data
_BLOCKED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
    "ALTER", "CREATE", "REPLACE", "MERGE", "CALL", "EXEC",
    "GRANT", "REVOKE",
}

_SELECT_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


@dataclass
class SafetyResult:
    safe: bool
    reason: str | None = None


def _extract_statement_types(sql: str) -> set[str]:
    """Return all top-level statement keywords found in the SQL."""
    parsed = sqlparse.parse(sql)
    types: set[str] = set()
    for statement in parsed:
        for token in statement.flatten():
            if token.ttype in (DDL, DML, Keyword):
                types.add(token.normalized.upper())
    return types


def validate_query(sql: str, allow_write: bool = False) -> SafetyResult:
    """
    Validate a generated SQL query for safety.

    - If allow_write is False (default / read-only mode), any DDL or DML
      other than SELECT is rejected.
    - Always requires the query to start with SELECT in read-only mode.
    - Logs the verdict for auditability.
    """
    stripped = sql.strip()

    if not stripped:
        result = SafetyResult(safe=False, reason="Empty query.")
        _log(sql, result)
        return result

    # Fast-path check: must be a SELECT in read-only mode
    if not allow_write:
        if not _SELECT_PATTERN.match(stripped):
            result = SafetyResult(
                safe=False,
                reason="Only SELECT queries are permitted in read-only mode.",
            )
            _log(sql, result)
            return result

    # Deep keyword check
    found_types = _extract_statement_types(stripped)
    blocked = found_types & _BLOCKED_KEYWORDS

    if blocked and not allow_write:
        result = SafetyResult(
            safe=False,
            reason=f"Query contains blocked operation(s): {', '.join(sorted(blocked))}.",
        )
        _log(sql, result)
        return result

    result = SafetyResult(safe=True)
    _log(sql, result)
    return result


def inject_row_limit(sql: str, limit: int | None = None) -> str:
    """
    Append LIMIT clause to a SELECT query if not already present.
    Uses settings.row_limit by default.
    """
    cap = limit or settings.row_limit
    stripped = sql.rstrip().rstrip(";")
    if re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        return sql  # already has a LIMIT
    return f"{stripped}\nLIMIT {cap};"


def _log(sql: str, result: SafetyResult) -> None:
    verdict = "SAFE" if result.safe else f"BLOCKED ({result.reason})"
    logger.info("Safety verdict: %s | SQL: %s", verdict, sql.replace("\n", " "))
