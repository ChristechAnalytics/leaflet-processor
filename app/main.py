from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.ocr_engine import run_ocr
from app.services.llm_parser import parse_text_to_json
import json
import os

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    # 1. OCR
    content = await file.read()
    raw_text = run_ocr(content)
    
    # 2. LLM Structuring
    structured_data = parse_text_to_json(raw_text)
    
    # 3. Save to data.json as requested
    output_path = os.path.join("data", "data.json")
    with open(output_path, "w") as f:
        json.dump(structured_data, f, indent=4)
        
    return structured_data