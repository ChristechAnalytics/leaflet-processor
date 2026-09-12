import csv
import io
import json
import os

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.services.llm_parser import parse_leaflet_image
from app.services.catalog_matcher import get_top_matches
from app.services import db

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    db.init_db()
    db.seed_catalog_if_empty()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    # 1. Vision LLM extraction (Gemini reads the leaflet image directly)
    content = await file.read()
    structured_data = parse_leaflet_image(content, file.content_type or "image/jpeg")

    # 2. Save raw extraction to data.json for continuity/debugging
    output_path = os.path.join("data", "data.json")
    with open(output_path, "w") as f:
        json.dump(structured_data, f, indent=4)

    # 3. Persist leaflet + extracted products, run catalog matching
    leaflet_id = db.create_leaflet(file.filename)

    items = []
    for product in structured_data:
        name = product.get("name", "")
        price = product.get("price", "")

        extracted_id = db.create_extracted_product(leaflet_id, name, price)
        candidates = get_top_matches(name, limit=5)
        if candidates:
            db.save_match_candidates(extracted_id, candidates)

        items.append(
            {
                "extracted_id": extracted_id,
                "name": name,
                "price": price,
                "candidates": candidates,
            }
        )

    return {"leaflet_id": leaflet_id, "items": items}


class SelectionRequest(BaseModel):
    extracted_id: int
    catalog_product_id: int


@app.post("/select")
async def select_match(selection: SelectionRequest):
    try:
        result = db.select_match(selection.extracted_id, selection.catalog_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@app.get("/leaflets/{leaflet_id}/export")
async def export_leaflet_csv(leaflet_id: int):
    if not db.leaflet_exists(leaflet_id):
        raise HTTPException(status_code=404, detail=f"No leaflet {leaflet_id}")

    rows = db.get_leaflet_export_rows(leaflet_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Extracted Name", "Extracted Price", "Status",
        "Matched Product", "Brand", "Category", "Unit Size", "Catalog Price", "SKU",
    ])
    for row in rows:
        writer.writerow([
            row["raw_name"],
            row["raw_price"],
            row["status"],
            row["matched_name"] or "",
            row["brand"] or "",
            row["category"] or "",
            row["unit_size"] or "",
            row["matched_price"] if row["matched_price"] is not None else "",
            row["sku"] or "",
        ])
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="leaflet_{leaflet_id}_products.csv"'},
    )


REQUIRED_CATALOG_COLUMNS = {"name", "price"}
OPTIONAL_CATALOG_COLUMNS = ["brand", "category", "unit_size", "sku"]


@app.get("/catalog/status")
async def catalog_status():
    return db.get_catalog_status()


@app.post("/catalog/upload")
async def upload_catalog(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Catalog file must be UTF-8 encoded CSV.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file has no header row.")

    header_map = {h.strip().lower(): h for h in reader.fieldnames}
    missing = REQUIRED_CATALOG_COLUMNS - header_map.keys()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required column(s): {', '.join(sorted(missing))}",
        )

    rows = []
    skipped = 0
    for raw_row in reader:
        name = (raw_row.get(header_map["name"]) or "").strip()
        price_str = (raw_row.get(header_map["price"]) or "").strip().lstrip("$")
        if not name:
            skipped += 1
            continue
        try:
            price = float(price_str)
        except ValueError:
            skipped += 1
            continue

        rows.append(
            {
                "name": name,
                "price": price,
                **{
                    col: (raw_row.get(header_map[col]) or "").strip() or None
                    for col in OPTIONAL_CATALOG_COLUMNS
                    if col in header_map
                },
                **{col: None for col in OPTIONAL_CATALOG_COLUMNS if col not in header_map},
            }
        )

    if not rows:
        raise HTTPException(status_code=400, detail="No valid rows found in the uploaded CSV.")

    db.replace_custom_catalog(rows)
    status = db.get_catalog_status()
    status["imported"] = len(rows)
    status["skipped"] = skipped
    return status


@app.post("/catalog/reset")
async def reset_catalog():
    db.reset_to_demo_catalog()
    return db.get_catalog_status()
