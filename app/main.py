from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.services.llm_parser import parse_leaflet_image
from app.services.catalog_matcher import get_top_matches
from app.services import db
import json
import os

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
