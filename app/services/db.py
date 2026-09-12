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
    price REAL,
    source TEXT DEFAULT 'demo'
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
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
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(catalog_products)")}
        if "source" not in columns:
            conn.execute("ALTER TABLE catalog_products ADD COLUMN source TEXT DEFAULT 'demo'")
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
            """INSERT INTO catalog_products (id, sku, name, brand, category, unit_size, price, source)
               VALUES (:id, :sku, :name, :brand, :category, :unit_size, :price, 'demo')""",
            catalog,
        )
        conn.commit()
    finally:
        conn.close()


def get_active_catalog_source() -> str:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'active_catalog_source'"
        ).fetchone()
        return row["value"] if row else "demo"
    finally:
        conn.close()


def set_active_catalog_source(source: str):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO app_settings (key, value) VALUES ('active_catalog_source', ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (source,),
        )
        conn.commit()
    finally:
        conn.close()


def get_catalog_status() -> dict:
    conn = get_connection()
    try:
        demo_count = conn.execute(
            "SELECT COUNT(*) FROM catalog_products WHERE source = 'demo'"
        ).fetchone()[0]
        custom_count = conn.execute(
            "SELECT COUNT(*) FROM catalog_products WHERE source = 'custom'"
        ).fetchone()[0]
        return {
            "active_source": get_active_catalog_source(),
            "demo_count": demo_count,
            "custom_count": custom_count,
        }
    finally:
        conn.close()


def replace_custom_catalog(rows: list):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM catalog_products WHERE source = 'custom'")
        conn.executemany(
            """INSERT INTO catalog_products (sku, name, brand, category, unit_size, price, source)
               VALUES (:sku, :name, :brand, :category, :unit_size, :price, 'custom')""",
            rows,
        )
        conn.execute(
            """INSERT INTO app_settings (key, value) VALUES ('active_catalog_source', 'custom')
               ON CONFLICT(key) DO UPDATE SET value = excluded.value"""
        )
        conn.commit()
    finally:
        conn.close()


def reset_to_demo_catalog():
    set_active_catalog_source("demo")


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


def get_leaflet_export_rows(leaflet_id: int) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT ep.id AS extracted_id, ep.raw_name, ep.raw_price, ep.status,
                      cp.sku, cp.name AS matched_name, cp.brand, cp.category,
                      cp.unit_size, cp.price AS matched_price
               FROM extracted_products ep
               LEFT JOIN catalog_products cp ON cp.id = ep.selected_catalog_id
               WHERE ep.leaflet_id = ?
               ORDER BY ep.id""",
            (leaflet_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def leaflet_exists(leaflet_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM leaflets WHERE id = ?", (leaflet_id,)).fetchone()
        return row is not None
    finally:
        conn.close()
