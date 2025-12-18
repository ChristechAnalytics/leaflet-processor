# Retail Leaflet Data Extraction Pipeline

## 📌 Project Overview
This project is a full-stack technical solution designed to automate the extraction of product information from unstructured retail leaflet images. It transforms raw image data into structured JSON and provides a user-friendly web interface for data verification and interaction.

---

## 🛠️ The Tech Stack
* **Backend:** FastAPI (Python) - Chosen for its high performance, native asynchronous support, and automatic OpenAPI documentation.
* **OCR Engine:** Pytesseract (Tesseract OCR) - An industry-standard open-source engine used for initial text localization and character recognition.
* **Data Structuring:** Gemini-3-flash-preview - Utilized as a "Semantic Brain" to parse messy OCR output into clean, structured data.
* **Frontend:** HTML5 & Tailwind CSS (via CDN) - Provides a modern, responsive UI without requiring a complex Node.js build pipeline.

---

## 🚀 Step-by-Step Process & Design Decisions

### 1. Project Architecture & Organization
**Decision:** I implemented a modular folder structure, separating core logic into a `services/` directory and routing into `main.py`.

**Why:** This follows the **Separation of Concerns** principle. By decoupling the OCR and LLM logic from the web framework, the system is easier to test and maintain. If the OCR engine needs to be upgraded in the future, only the service file requires modification.

### 2. Image Pre-processing
**Decision:** I integrated the `Pillow` library to convert images to grayscale and increase contrast before sending them to the OCR engine.

**Why:** Retail leaflets often use white text inside dark or red circles (as seen in the provided image). Standard OCR can struggle with these high-contrast areas. Pre-processing "flattens" the image, making character boundaries clearer for Tesseract.

### 3. OCR (Optical Character Recognition)
**Decision:** I utilized Pytesseract with specific configuration flags (`--psm 3`) to handle automatic page segmentation.

**Why:** Since retail leaflets are non-linear (grid-based layouts), the OCR needs to look for sparse text fragments rather than traditional top-to-bottom sentences.

### 4. Semantic Parsing (LLM Layer)
**Decision:** I chose an LLM over Regular Expressions (Regex) for data structuring.

**Why:** Leaflets often place weights (e.g., "500g") closer to the product name than the actual price ($2.49). An LLM uses Natural Language Understanding to distinguish between a "unit of measurement" and a "monetary value," which is nearly impossible to do reliably with Regex in a noisy OCR environment.

### 5. Frontend Interaction
**Decision:** I built a dynamic table with clickable rows using Tailwind CSS.

**Why:** Per the assessment requirements, this simulates a real-world "human-in-the-loop" workflow where a user can select specific extracted items for further downstream processing (like inventory updates or price matching).

---

## 📥 Installation & Setup

### 1. Prerequisites
* **Tesseract OCR:** Must be installed on your operating system, and also include the path (e.g [pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'])
* **Python 3.9+**
* **OpenAI API Key**

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
