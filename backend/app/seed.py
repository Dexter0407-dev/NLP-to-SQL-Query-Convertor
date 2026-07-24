"""
Seeds a sample SQLite database for demo purposes.
Run once: python -m app.seed
"""
from __future__ import annotations

import random
import sqlite3

DB_PATH = "./sample.db"

CATEGORIES = ["Electronics", "Furniture", "Apparel", "Groceries", "Toys"]
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = {
    "Electronics": ["Wireless Mouse", "USB-C Hub", "Bluetooth Speaker", "Laptop Stand", "Webcam"],
    "Furniture": ["Office Chair", "Standing Desk", "Bookshelf", "Bar Stool", "Filing Cabinet"],
    "Apparel": ["Cotton T-Shirt", "Denim Jacket", "Running Shoes", "Wool Sweater", "Rain Coat"],
    "Groceries": ["Basmati Rice", "Olive Oil", "Green Tea", "Almonds", "Honey Jar"],
    "Toys": ["Building Blocks", "RC Car", "Puzzle Set", "Action Figure", "Board Game"],
}


def seed() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            product     TEXT NOT NULL,
            category    TEXT NOT NULL,
            region      TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            price       REAL NOT NULL,
            order_date  TEXT NOT NULL
        );
    """)

    cursor.execute("DELETE FROM orders;")  # clear existing data

    rows = []
    for _ in range(100):
        category = random.choice(CATEGORIES)
        product = random.choice(PRODUCTS[category])
        region = random.choice(REGIONS)
        quantity = random.randint(1, 8)
        price = round(random.uniform(15, 200), 2)
        year = "2024" if random.random() > 0.35 else "2023"
        month = str(random.randint(1, 12)).zfill(2)
        day = str(random.randint(1, 28)).zfill(2)
        rows.append((product, category, region, quantity, price, f"{year}-{month}-{day}"))

    cursor.executemany("""
        INSERT INTO orders (product, category, region, quantity, price, order_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    print(f"✅  Seeded {len(rows)} rows into {DB_PATH}")


if __name__ == "__main__":
    seed()
