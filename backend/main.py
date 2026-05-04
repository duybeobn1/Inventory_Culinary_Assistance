import os
import re
import json
import cv2
import numpy as np
from typing import Dict
from fastapi import FastAPI, UploadFile, File
from google import genai
from google.genai import types
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Culinary AI Inventory System")

# Configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize external clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

def clean_ai_json(raw_text: str) -> Dict:
    """Removes markdown formatting blocks and parses the JSON string."""
    clean_text = re.sub(r'```json\n?|```', '', raw_text).strip()
    return json.loads(clean_text)

def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Deskew algorithm: Detects the skew angle of the text lines
    on the receipt and rotates the image to straighten it.
    """
    # Convert to grayscale for calculation
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Invert colors (white text, black background) to find text pixel coordinates
    gray = cv2.bitwise_not(gray)
    
    # Binarize the image (keep only absolute black and white)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    # Get coordinates of all text pixels (pixel values > 0)
    coords = np.column_stack(np.where(thresh > 0))
    
    # Find the minimum area bounding rectangle that encloses all text
    # This returns (center(x, y), (width, height), angle of rotation)
    angle = cv2.minAreaRect(coords)[-1]
    
    # Handle the angle interpretation based on OpenCV version logic
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # If the image is almost straight, skip rotation to avoid blurriness
    if abs(angle) < 0.5:
        return image

    # Perform the affine transformation to rotate the image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # borderMode=cv2.BORDER_REPLICATE fills the empty corners after rotation 
    # with the background color of the image edges
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def preprocess_receipt_image(image_bytes: bytes) -> bytes:
    """
    Complete image preprocessing pipeline for OCR:
    Deskew -> Grayscale -> Denoise -> Contrast Enhancement.
    """
    # 1. Load image from bytes into OpenCV format
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 2. Deskew: Straighten the image
    straight_img = deskew_image(img)

    # 3. Denoise: Smooth out grain from low-light captures
    gray = cv2.cvtColor(straight_img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Contrast Enhancement: Apply CLAHE to make text stand out against the background
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)

    # 5. Encode back to JPEG bytes for API transmission
    _, encoded_img = cv2.imencode('.jpg', enhanced)
    return encoded_img.tobytes()

def get_or_create_ingredient(raw_name: str) -> int:
    """
    Canonicalization Layer: Normalizes extracted ingredient names 
    against the PostgreSQL database via Supabase REST API.
    """
    # Check if ingredient exists (case-insensitive)
    res = supabase.table('ingredients').select('id').ilike('name', raw_name).execute()
    
    if len(res.data) > 0:
        return res.data[0]['id']
    
    # Create new ingredient entry if not found
    new_res = supabase.table('ingredients').insert({
        "name": raw_name.upper(),
        "category": "Uncategorized"
    }).execute()
    return new_res.data[0]['id']

@app.get("/")
def read_root():
    """Root health check endpoint."""
    return {"status": "Serverless API is running!", "backend": "Supabase REST API"}

@app.get("/health/db")
def check_db_connection():
    """Verify Supabase connection by fetching a single ingredient."""
    try:
        res = supabase.table('ingredients').select("*").limit(1).execute()
        return {"status": "success", "message": "Connected to Supabase REST API"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/receipt/parse")
async def parse_and_sync_inventory(file: UploadFile = File(...)):
    """
    Core Milestone 2 Microservice: 
    Accepts an image, preprocesses it, extracts structured JSON using Gemini Flash Lite, 
    and synchronizes the normalized data with the inventory database.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not configured in the environment"}

    try:
        # Read raw image upload
        raw_image_bytes = await file.read()
        
        # Stabilize and preprocess the image
        processed_image_bytes = preprocess_receipt_image(raw_image_bytes)
        
        prompt = """
        Analyze this receipt. Return ONLY a valid JSON.
        Instructions: 
        1. Canonicalize names: Extract the core ingredient (e.g., 'POTATO CHIPS' instead of 'Hrtland Potato Chpssthrn Salt 150g').
        2. Mass Calculation (CRITICAL): If the product name contains a weight or volume (e.g., 150g, 4x90g) AND there is a billing multiplier (e.g., Qty 2), you MUST multiply them to output the total physical net amount. 
           - Example A: 'Chips 150g Qty 2' MUST output "qty": 300, "unit": "g".
           - Example B: 'Dove Bar 4x90g' MUST output "qty": 360, "unit": "g".
        3. Strict Units: Force all units to be kg, g, l, ml. Only fallback to 'unit' if absolutely no mass/volume is printed (e.g., Eggs). Never use 'each' or 'pk'.
        Format: {"vendor": "string", "date": "YYYY-MM-DD", "items": [{"name": "CLEAN_NAME", "qty": 1.0, "unit": "g", "price": 0.0}], "total": 0.0}
        """

        # Transmit preprocessed image to Gemini 2.5 Flash Lite
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, types.Part.from_bytes(data=processed_image_bytes, mime_type="image/jpeg")]
        )
        
        data = clean_ai_json(response.text)

        # Record the transaction metadata
        receipt_res = supabase.table('receipts').insert({
            "vendor": data.get('vendor'),
            "date": data.get('date'),
            "total_amount": data.get('total')
        }).execute()
        receipt_id = receipt_res.data[0]['id']

        processed_items = []
        
        # Iterate and sync line items
        for item in data.get('items', []):
            # Canonicalize ingredient name
            ingredient_id = get_or_create_ingredient(item['name'])
            
            # Persist line item details
            supabase.table('receipt_line').insert({
                "receipt_id": receipt_id,
                "ingredient_id": ingredient_id,
                "quantity": item['qty'],
                "price": item['price']
            }).execute()

            # Execute Inventory Upsert Logic
            inv_check = supabase.table('inventory').select('current_quantity').eq('ingredient_id', ingredient_id).execute()
            
            if len(inv_check.data) > 0:
                # Accumulate quantity for existing stock
                new_qty = inv_check.data[0]['current_quantity'] + item['qty']
                supabase.table('inventory').update({"current_quantity": new_qty}).eq('ingredient_id', ingredient_id).execute()
            else:
                # Initialize new stock entry
                supabase.table('inventory').insert({
                    "ingredient_id": ingredient_id,
                    "current_quantity": item['qty'],
                    "unit": item.get('unit', 'unit')
                }).execute()
            
            processed_items.append({"ingredient_id": ingredient_id, "name": item['name']})

        return {
            "status": "Inventory Synchronized Successfully",
            "receipt_id": receipt_id,
            "items_synced": processed_items
        }

    except Exception as e:
        return {"error": str(e)}