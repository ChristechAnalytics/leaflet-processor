import json
import os
import sqlite3

DB_PATH = os.path.join("data", "app.db")
CATALOG_PATH = os.path.join("data", "catalog.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog_products (
    id INTEGER PRIMARY KEY,
    sku TEXT,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    unit_size TEXT,
    price REAL
);

CREATE TABLE IF NOT EXISTS leaflets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extracted_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leaflet_id INTEGER REFERENCES leaflets(id),
    raw_name TEXT,
    raw_price TEXT,
    status TEXT DEFAULT 'pending',
    selected_catalog_id INTEGER REFERENCES catalog_products(id),
    selected_at TEXT
);

CREATE TABLE IF NOT EXISTS match_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extracted_product_id INTEGER REFERENCES extracted_products(id),
    catalog_product_id INTEGER REFERENCES catalog_products(id),
    score REAL,
    rank INTEGER
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_catalog_if_empty():
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM catalog_products").fetchone()[0]
        if count > 0:
            return
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        conn.executemany(
            """INSERT INTO catalog_products (id, sku, name, brand, category, unit_size, price)
               VALUES (:id, :sku, :name, :brand, :category, :unit_size, :price)""",
            catalog,
        )
        conn.commit()
    finally:
        conn.close()


def create_leaflet(filename: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO leaflets (filename) VALUES (?)", (filename,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def create_extracted_product(leaflet_id: int, raw_name: str, raw_price: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO extracted_products (leaflet_id, raw_name, raw_price) VALUES (?, ?, ?)",
            (leaflet_id, raw_name, raw_price),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_match_candidates(extracted_product_id: int, candidates: list):
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT INTO match_candidates (extracted_product_id, catalog_product_id, score, rank)
               VALUES (?, ?, ?, ?)""",
            [
                (extracted_product_id, c["catalog_product_id"], c["score"], rank)
                for rank, c in enumerate(candidates, start=1)
            ],
        )
        conn.commit()
    finally:
        conn.close()


def select_match(extracted_id: int, catalog_product_id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE extracted_products
               SET selected_catalog_id = ?, status = 'matched', selected_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (catalog_product_id, extracted_id),
        )
        conn.commit()
        row = conn.execute(
            """SELECT ep.id AS extracted_id, ep.raw_name, ep.raw_price, ep.status, ep.selected_at,
                      cp.id AS catalog_product_id, cp.name AS catalog_name, cp.brand, cp.price AS catalog_price
               FROM extracted_products ep
               JOIN catalog_products cp ON cp.id = ep.selected_catalog_id
               WHERE ep.id = ?""",
            (extracted_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"No extracted product {extracted_id} with a valid selection")
        return dict(row)
    finally:
        conn.close()
