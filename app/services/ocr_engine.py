import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image, ImageOps, ImageEnhance
import io

def run_ocr(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    
    # Pre-processing: Convert to Grayscale and increase contrast
    # This helps Tesseract distinguish white text inside red circles
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    
    # psm 11: Sparse text - finds as much text as possible in no particular order
    # psm 3: Fully automatic page segmentation (Standard)
    custom_config = r'--oem 3 --psm 3' 
    
    return pytesseract.image_to_string(image, config=custom_config)