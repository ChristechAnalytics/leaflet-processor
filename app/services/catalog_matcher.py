from rapidfuzz import process, fuzz, utils

from app.services.db import get_connection


def get_top_matches(raw_name: str, limit: int = 5) -> list:
    """Fuzzy-matches raw_name against the catalog and returns the top `limit` candidates."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, brand, category, unit_size, price FROM catalog_products"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    choices = {row["id"]: row["name"] for row in rows}
    by_id = {row["id"]: dict(row) for row in rows}

    matches = process.extract(
        raw_name,
        choices,
        scorer=fuzz.WRatio,
        processor=utils.default_process,
        limit=limit,
    )

    results = []
    for _name, score, catalog_id in matches:
        product = by_id[catalog_id]
        results.append(
            {
                "catalog_product_id": product["id"],
                "name": product["name"],
                "brand": product["brand"],
                "category": product["category"],
                "unit_size": product["unit_size"],
                "price": product["price"],
                "score": round(score, 2),
            }
        )
    return results
