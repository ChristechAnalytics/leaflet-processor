# Retail Leaflet Data Extraction Pipeline

## 📌 Project Overview
This project is a full-stack technical solution designed to automate the extraction of product information from unstructured retail leaflet images, match each extracted product against a catalog, and let a human confirm the correct match. It transforms raw image data into structured JSON, ranks the top 5 catalog candidates per product, and provides a human-in-the-loop (HITL) web interface for review and confirmation, with results persisted to a database.

---

## 🛠️ The Tech Stack
* **Backend:** FastAPI (Python) - Chosen for its high performance, native asynchronous support, and automatic OpenAPI documentation.
* **Vision Extraction:** Gemini-3-flash-preview (via its OpenAI-compatible API, using the `openai` SDK) - The leaflet image is sent directly to the vision-capable LLM, which reads the layout and returns clean, structured product data in one call.
* **Catalog Matching:** RapidFuzz - Fuzzy string matching ranks the 5 closest catalog products for each extracted item, since LLM-extracted names rarely match catalog names exactly.
* **Database:** SQLite (`data/app.db`) - Stores the catalog, each extraction run, its match candidates, and the HITL-confirmed selection.
* **Frontend:** HTML5 & Tailwind CSS (via CDN) - Provides a modern, responsive UI without requiring a complex Node.js build pipeline.

---

## 🚀 Step-by-Step Process & Design Decisions

### 1. Project Architecture & Organization
**Decision:** I implemented a modular folder structure, separating core logic into a `services/` directory and routing into `main.py`.

**Why:** This follows the **Separation of Concerns** principle. By decoupling the extraction logic from the web framework, the system is easier to test and maintain. If the extraction approach needs to change in the future, only the service file requires modification.

### 2. Vision LLM Extraction (instead of OCR + text parsing)
**Decision:** The leaflet image is sent directly to Gemini's vision-capable endpoint in a single call, instead of running local OCR (Tesseract) to flatten it into text first and then structuring that text with a second LLM call.

**Why:** Retail leaflets are non-linear (grid-based layouts) with prices often shown as large digits inside colored circles positioned near — but not always directly beside — the product they belong to. OCR discards that visual layout, leaving a second LLM pass to guess at pairings from text order alone. A vision LLM sees the actual image, so it can use spatial/visual cues (proximity, badge styling) to pair prices with products directly, in one step, with no dependency on a local OCR binary.

### 3. Semantic Parsing (LLM Layer)
**Decision:** I chose an LLM over Regular Expressions (Regex) for data structuring.

**Why:** Leaflets often place weights (e.g., "500g") closer to the product name than the actual price ($2.49). An LLM uses Natural Language Understanding to distinguish between a "unit of measurement" and a "monetary value," which is nearly impossible to do reliably with Regex.

### 4. Catalog Matching
**Decision:** I used RapidFuzz to fuzzy-match each extracted product name against a product catalog (`data/catalog.json`, a synthetic catalog seeded into SQLite on startup) and return the top 5 ranked candidates per product.

**Why:** LLM-extracted names rarely match catalog names verbatim (abbreviations, missing brand names, formatting differences), so exact lookups fail too often. Fuzzy string similarity is fast, free, and deterministic, and surfacing the top 5 (rather than a single best guess) leaves room for the human reviewer to pick correctly when the top match is wrong.

### 5. Human-in-the-Loop (HITL) Review & Persistence
**Decision:** For each extracted product, the UI shows its top 5 catalog candidates (name, brand, price, match score) as selectable options. Confirming a selection calls `POST /select`, which writes the chosen catalog product back onto the extraction record in SQLite.

**Why:** Automated matching alone isn't reliable enough for retail data (ambiguous extraction, near-duplicate catalog entries). Keeping a human in the loop to confirm the match, with the result persisted to a database, models a realistic downstream workflow (e.g. inventory updates or price matching) rather than blindly trusting the top-ranked match.

---

## 📥 Installation & Setup

### 1. Prerequisites
* **Python 3.9+**
* **Gemini API Key** (used via Gemini's OpenAI-compatible endpoint, through the `openai` SDK, for vision-based extraction)

### 2. Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Create a .env file in the root directory and add your key:
source root_directory/.env

# Add your API key in the .env file
GEMINI_API_KEY=your_actual_key_here
```

### 4: Run the Application
```bash
# Run the Application
uvicorn app.main:app --reload

# Open your browser to: 
http://127.0.0.1:8000
```

On first run, a SQLite database is created at `data/app.db` and seeded with the synthetic catalog from `data/catalog.json`. Upload a leaflet image, review the top 5 catalog matches per extracted product, and click "Confirm match" to persist the selection back to the database.

---

## ☁️ Deployment

This app now has no OS-level dependency (extraction happens via a vision LLM call instead of a local Tesseract binary), but it still writes to a local SQLite file (`data/app.db`) on startup and on every confirmed match. That still rules out a serverless platform like Vercel, whose filesystem is read-only outside of an ephemeral `/tmp` — `db.init_db()` would fail before a single request is served. Deploy the Docker image instead, to a host that runs a long-lived container with a real writable disk — e.g. **Render**, Railway, or Fly.io. (If you later want true serverless portability, the remaining step is swapping SQLite for a hosted database.)

### Deploying to Render
1. Push this repo to GitHub (if not already).
2. In the Render dashboard, choose **New + Blueprint** and point it at this repo — it will pick up [render.yaml](render.yaml) and build the [Dockerfile](Dockerfile) automatically.
3. When prompted, set the `GEMINI_API_KEY` environment variable (it's marked `sync: false` in the blueprint so Render will ask for it rather than storing it in the repo).
4. Deploy. Render sets `$PORT` automatically, which the Dockerfile's `CMD` already respects.

`render.yaml` pins `plan: free` so this deploys on Render's free web service instance (spins down on inactivity, wakes on the next request) — it costs $0. Render may still ask for a card during account signup for identity verification; that's separate from billing, and you won't be charged as long as you stay on the free instance type.

**Note on persistence:** by default, Render's web service filesystem is ephemeral — `data/app.db` resets on every redeploy or restart. The catalog reseeds itself automatically from `data/catalog.json` on startup, but any confirmed HITL selections will be lost when the container restarts. For real persistence, attach a [Render persistent disk](https://render.com/docs/disks) mounted at `/app/data`, or migrate from SQLite to a managed database (e.g. Render's free Postgres tier).
