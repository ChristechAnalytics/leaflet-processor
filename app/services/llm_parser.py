import base64
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

EXTRACTION_PROMPT = """
You are a Retail Data Extractor analyzing an image of a multi-product grocery leaflet.

TASK:
1. Carefully examine the image and identify EVERY distinct product advertised.
2. For each product, extract its full product name/description exactly as printed.
3. For each product, extract its price. Prices are often shown as large digits inside
   colored circles or badges, positioned above, below, or beside the product it belongs
   to — use visual layout and design conventions (not just text order) to pair each
   price with the correct product.
4. Normalize price formats: if you see "99c" or "99¢", convert it to "$0.99". Always
   output prices as "$X.XX".

OUTPUT:
Return a JSON object with a "products" key containing the full list.
Example: {"products": [{"name": "Apples", "price": "$1.99"}, ...]}
"""


def parse_leaflet_image(image_bytes: bytes, mime_type: str = "image/jpeg"):
    """Uses a vision-capable LLM to extract structured product data directly from a leaflet image."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                ],
            }
        ],
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    return data.get("products", data) if isinstance(data, dict) else data
