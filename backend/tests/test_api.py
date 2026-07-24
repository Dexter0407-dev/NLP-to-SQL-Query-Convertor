"""
Smoke tests for the NL-to-SQL FastAPI backend.
These run without a real LLM key — they test everything except the LLM call.
"""
import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')

# Seed into the test DB path
import sqlite3, random
_DB = "./test.db"
conn = sqlite3.connect(_DB)
conn.execute("""CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT, category TEXT,
    region TEXT, quantity INTEGER, price REAL, order_date TEXT)""")
conn.execute("DELETE FROM orders")
conn.executemany("INSERT INTO orders(product,category,region,quantity,price,order_date) VALUES(?,?,?,?,?,?)",
    [("Widget","Electronics","North",2,49.99,"2024-01-15"),
     ("Chair","Furniture","South",1,199.99,"2024-02-20"),
     ("T-Shirt","Apparel","East",3,19.99,"2023-11-05")])
conn.commit(); conn.close()

from app.main import app  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["llm_provider"] == "groq"


def test_schema_returns_tables():
    resp = client.get("/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert "tables" in data
    assert len(data["tables"]) >= 1
    table = data["tables"][0]
    assert "name" in table
    assert "columns" in table


def test_preview_orders():
    resp = client.get("/preview/orders?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] >= 1
    assert "columns" in data
    assert "results" in data


def test_preview_invalid_table():
    resp = client.get("/preview/nonexistent_table")
    assert resp.status_code == 400


def test_upload_csv():
    csv_content = b"product,price,qty\nWidget,9.99,10\nGadget,19.99,5\n"
    resp = client.post(
        "/upload",
        files={"file": ("test_data.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_name"] == "test_data"
    assert data["row_count"] == 2
    assert len(data["columns"]) == 3


def test_upload_non_csv_rejected():
    resp = client.post(
        "/upload",
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert resp.status_code == 400


def test_query_requires_question():
    resp = client.post("/query", json={"question": "", "allow_write": False})
    assert resp.status_code == 422


def test_safety_blocks_write(monkeypatch):
    """Safety layer must block destructive SQL even if LLM returns it."""
    from app import safety
    result = safety.validate_query("DROP TABLE orders;", allow_write=False)
    assert result.safe is False

    result = safety.validate_query("SELECT * FROM orders;", allow_write=False)
    assert result.safe is True
