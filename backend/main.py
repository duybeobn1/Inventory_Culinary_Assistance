import os
import re
import json
import cv2
import numpy as np
import base64
from typing import Dict
from fastapi import FastAPI, UploadFile, File
from zai import ZaiClient
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Culinary AI Inventory System")

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ZAI_API_KEY = os.getenv("ZAI_API_KEY")

# Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
zai_client = ZaiClient(api_key=ZAI_API_KEY)

def clean_ai_json(raw_text: str) -> Dict:
    """Removes markdown formatting blocks and parses the JSON string."""
    clean_text = re.sub(r'```json\n?|```', '', raw_text).strip()
    return json.loads(clean_text)

def deskew_image(image: np.ndarray) -> np.ndarray:
    """Straightens the image based on text line orientation."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def preprocess_receipt_image(image_bytes: bytes) -> bytes:
    """Full preprocessing pipeline: Deskew -> Denoise -> Enhancement."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    straight_img = deskew_image(img)
    gray = cv2.cvtColor(straight_img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    _, encoded_img = cv2.imencode('.jpg', enhanced)
    return encoded_img.tobytes()

def get_or_create_ingredient(raw_name: str) -> int:
    """Syncs ingredient names with the Supabase database."""
    res = supabase.table('ingredients').select('id').ilike('name', raw_name).execute()
    
    if len(res.data) > 0:
        return res.data[0]['id']
    
    new_res = supabase.table('ingredients').insert({
        "name": raw_name.upper(),
        "category": "Uncategorized"
    }).execute()
    return new_res.data[0]['id']

@app.get("/health/db")
def check_db_connection():
    try:
        supabase.table('ingredients').select("*").limit(1).execute()
        return {"status": "success", "message": "Connected to Supabase"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/receipt/parse")
async def parse_and_sync_inventory(file: UploadFile = File(...)):
    """OCR Microservice using GLM-4.6V-Flash."""
    if not ZAI_API_KEY:
        return {"error": "ZAI_API_KEY missing"}

    try:
        # Image Processing
        raw_image_bytes = await file.read()
        processed_bytes = preprocess_receipt_image(raw_image_bytes)
        
        # Prepare Base64 for GLM Vision API
        base64_image = base64.b64encode(processed_bytes).decode('utf-8')

        prompt = """
        Analyze this receipt. Return ONLY a valid JSON.
        Instructions: 
        1. Canonicalize names: Extract the core ingredient name.
        2. Mass Calculation: If product name contains a weight (e.g., 150g) and Qty > 1, multiply them for total mass.
        3. Strict Units: Use kg, g, l, ml. Default to 'unit'.
        Format: {"vendor": "string", "date": "YYYY-MM-DD", "items": [{"name": "NAME", "qty": 1.0, "unit": "g", "price": 0.0}], "total": 0.0}
        """

        # GLM-4.6V-Flash Vision Request
        response = zai_client.chat.completions.create(
            model="glm-4.6v-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
        )
        
        data = clean_ai_json(response.choices[0].message.content)

        # Database Sync
        receipt_res = supabase.table('receipts').insert({
            "vendor": data.get('vendor'),
            "date": data.get('date'),
            "total_amount": data.get('total')
        }).execute()
        receipt_id = receipt_res.data[0]['id']

        sync_log = []
        for item in data.get('items', []):
            ing_id = get_or_create_ingredient(item['name'])
            
            # Record receipt line
            supabase.table('receipt_line').insert({
                "receipt_id": receipt_id, "ingredient_id": ing_id,
                "quantity": item['qty'], "price": item['price']
            }).execute()

            # Inventory Upsert
            inv = supabase.table('inventory').select('current_quantity').eq('ingredient_id', ing_id).execute()
            if len(inv.data) > 0:
                new_qty = inv.data[0]['current_quantity'] + item['qty']
                supabase.table('inventory').update({"current_quantity": new_qty}).eq('ingredient_id', ing_id).execute()
            else:
                supabase.table('inventory').insert({
                    "ingredient_id": ing_id, "current_quantity": item['qty'], "unit": item.get('unit', 'unit')
                }).execute()
            
            sync_log.append({"name": item['name'], "qty": item['qty']})

        return {"status": "Success", "model": "GLM-4.6V-Flash", "items": sync_log}

    except Exception as e:
        return {"error": str(e)}