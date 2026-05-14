import os
import cv2
import json
import base64
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from google.genai import types

# Assuming you created schemas.py in the previous step
from schemas import IngredientCreate, IngredientResponse 
from database import supabase, ai_client, clean_ai_json, get_or_create_ingredient

router = APIRouter(tags=["Fridge Scanning"])

def load_capacities():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "ingredient_capacities.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"CRITICAL: Could not find {file_path}")
        return {"MILK": {"capacity": 1000, "unit": "ml"}}

CAPACITY_MAP = load_capacities()

def get_image_crop(image_np: np.ndarray, box_coords: list) -> str:
    h, w = image_np.shape[:2]
    ymin, xmin, ymax, xmax = box_coords
    
    left, top = int(xmin * w / 1000), int(ymin * h / 1000)
    right, bottom = int(xmax * w / 1000), int(ymax * h / 1000)
    
    left, top = max(0, left), max(0, top)
    right, bottom = min(w, right), min(h, bottom)
    
    crop = image_np[top:bottom, left:right]
    if crop.size == 0:
        return ""
        
    _, buffer = cv2.imencode('.jpg', crop)
    return base64.b64encode(buffer).decode('utf-8')

# --- 1. EXISTING: AI VOLUMETRIC SCANNING ---
@router.post("/api/scan_fridge")
async def scan_fridge_prediction(file: UploadFile = File(...)):
    try:
        raw_bytes = await file.read()
        nparr = np.frombuffer(raw_bytes, np.uint8)
        original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        spatial_prompt = """
        Analyze this fridge interior as a volumetric analyst.
        For every visible ingredient or prepared meal:
        1. Identify the name and estimate the 'visible volume fraction' (0.0 to 1.0).
        2. Provide normalized bounding box coordinates [ymin, xmin, ymax, xmax] for the item.
        Return ONLY a JSON list: [{"name": "MILK", "volume_fraction": 0.75, "box": [ymin, xmin, ymax, xmax]}]
        """

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[spatial_prompt, types.Part.from_bytes(data=raw_bytes, mime_type="image/jpeg")]
        )
        
        predictions = clean_ai_json(response.text)
        verification_data = []
        
        for item in predictions:
            name = item['name'].upper()
            fraction = item['volume_fraction']
            box = item.get('box', [0, 0, 0, 0])
            
            spec = CAPACITY_MAP.get(name, {"capacity": 1.0, "unit": "unit"})
            estimated_mass = round(fraction * spec['capacity'], 2)
            crop_b64 = get_image_crop(original_img, box)
            
            verification_data.append({
                "thumbnail": f"data:image/jpeg;base64,{crop_b64}" if crop_b64 else None,
                "name": name,
                "predicted_fraction": fraction,
                "estimated_mass": estimated_mass,
                "unit": spec['unit']
            })

        return {"status": "verification_required", "data": verification_data}

    except Exception as e:
        return {"error": str(e)}

@router.post("/api/inventory/confirm_scan")
async def confirm_inventory_update(confirmed_data: list):
    try:
        updated_items = []
        for item in confirmed_data:
            # We will update this function in database.py to fetch TCM properties
            ingredient_id = get_or_create_ingredient(item['name']) 
            
            supabase.table('inventory').upsert({
                "ingredient_id": ingredient_id,
                "current_quantity": item['estimated_mass'],
                "unit": item.get('unit', 'g'),
                "last_updated": "now()"
            }, on_conflict="ingredient_id").execute()
            
            updated_items.append(item['name'])

        return {"status": "success", "synced_count": len(updated_items)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 2. NEW: MANUAL ADDITION WITH TCM ATTRIBUTES ---
@router.post("/api/fridge/manual_add", response_model=IngredientResponse)
def manual_add_ingredient(ingredient: IngredientCreate):
    """
    Allows manual insertion of an ingredient with explicit 
    Yin-Yang and Five Elements philosophical properties.
    """
    try:
        data_to_insert = ingredient.model_dump()
        
        # 1. Insert the philosophical base ingredient
        ing_response = supabase.table("ingredients").insert({
            "name": data_to_insert["name"],
            "thermal_property": data_to_insert.get("thermal_property"),
            "five_element": data_to_insert.get("five_element"),
            "tastes": data_to_insert.get("tastes", [])
        }).execute()
        
        if not ing_response.data:
            raise HTTPException(status_code=400, detail="Failed to insert ingredient")
            
        new_ingredient = ing_response.data[0]
        
        # 2. Update the user's inventory quantity
        supabase.table("inventory").upsert({
            "ingredient_id": new_ingredient["id"],
            "current_quantity": data_to_insert["quantity"],
            "unit": data_to_insert["unit"],
            "last_updated": "now()"
        }).execute()
            
        return new_ingredient
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))