from pydantic import BaseModel, Field
from typing import Any, List, Optional, Dict


# ── Request / Response schemas ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Natural language question about the data")
    allow_write: bool = Field(False, description="Opt-in to allow write operations")


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True


class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]
    row_count: Optional[int] = None


class SchemaResponse(BaseModel):
    tables: List[TableInfo]
    database_type: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: List[str]
    results: List[Dict[str, Any]]
    row_count: int
    safe: bool
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_provider: str


class ErrorResponse(BaseModel):
    detail: str
    code: str
