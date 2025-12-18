import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"), 
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def parse_text_to_json(raw_text: str):
    """Uses LLM to structure messy OCR text into clean JSON."""
    prompt = f"""
    You are a Retail Data Extractor. I am providing OCR text from a multi-product grocery leaflet.
    
    OCR TEXT:
    {raw_text}

    TASK:
    1. Extract EVERY product visible in the text.
    2. For each product, find the price (usually a 3 or 4 digit number like 1.99, 2.49, 0.99).
    3. Note: In this leaflet, prices are often listed BEFORE or ABOVE the product name.
    4. If you see "99c", convert it to "$0.99".
    
    OUTPUT:
    Return a JSON object with a "products" key containing the full list.
    Example: {{"products": [{{"name": "Apples", "price": "$1.99"}}, ...]}}
    """

    
    response = client.chat.completions.create(
            model="gemini-3-flash-preview", 
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
    
    data = json.loads(response.choices[0].message.content)
    return data.get("products", data) if isinstance(data, dict) else data
