import os
import json
import cv2
import base64
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from google.genai import types
from pydantic import BaseModel
from typing import Optional
from db.supabase import supabase
from db.ai import ai_client, clean_ai_json
from services.ingredient_service import get_or_create_ingredient
from dependencies import get_current_user
from logging_config import logger

router = APIRouter(tags=["Fridge Scanning"])


def load_capacities() -> dict:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "ingredient_capacities.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Could not find {file_path}, using default capacity map")
        return {"MILK": {"capacity": 1000, "unit": "ml"}}


CAPACITY_MAP = load_capacities()


class FridgeItemPrediction(BaseModel):
    name: str
    volume_fraction: float
    box: list[float] = [0.0, 0.0, 0.0, 0.0]


class FridgeScanResponse(BaseModel):
    status: str
    data: list[dict]


class ConfirmedFridgeItem(BaseModel):
    name: str
    estimated_mass: float
    unit: str = "g"
    thumbnail: Optional[str] = None


def get_image_crop(image_np: np.ndarray, box_coords: list) -> str:
    h, w = image_np.shape[:2]
    ymin, xmin, ymax, xmax = box_coords

    left = max(0, int(xmin * w / 1000))
    top = max(0, int(ymin * h / 1000))
    right = min(w, int(xmax * w / 1000))
    bottom = min(h, int(ymax * h / 1000))

    crop = image_np[top:bottom, left:right]
    if crop.size == 0:
        return ""

    _, buffer = cv2.imencode(".jpg", crop)
    return base64.b64encode(buffer).decode("utf-8")


@router.post("/api/scan_fridge")
async def scan_fridge_prediction(file: UploadFile = File(...)):
    try:
        raw_bytes = await file.read()
        original_img = cv2.imdecode(
            np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR
        )

        spatial_prompt = """
        Analyze this fridge interior as a volumetric analyst.
        For every visible ingredient or prepared meal:
        1. Identify the name and estimate the 'visible volume fraction' (0.0 to 1.0).
        2. Provide normalized bounding box coordinates [ymin, xmin, ymax, xmax] for the item.
        Return ONLY a JSON list: [{"name": "MILK", "volume_fraction": 0.75, "box": [ymin, xmin, ymax, xmax]}]
        """

        response = ai_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                spatial_prompt,
                types.Part.from_bytes(data=raw_bytes, mime_type="image/jpeg"),
            ],
        )

        predictions = clean_ai_json(response.text)
        verification_data = []

        for item in predictions:
            name = item["name"].upper()
            fraction = item["volume_fraction"]
            box = item.get("box", [0.0, 0.0, 0.0, 0.0])

            spec = CAPACITY_MAP.get(name, {"capacity": 1.0, "unit": "unit"})
            estimated_mass = round(fraction * spec["capacity"], 2)
            crop_b64 = get_image_crop(original_img, box)

            verification_data.append(
                {
                    "thumbnail": f"data:image/jpeg;base64,{crop_b64}" if crop_b64 else None,
                    "name": name,
                    "predicted_fraction": fraction,
                    "estimated_mass": estimated_mass,
                    "unit": spec["unit"],
                }
            )

        return {"status": "verification_required", "data": verification_data}

    except Exception as e:
        logger.exception("Fridge scan failed")
        raise HTTPException(status_code=500, detail=f"Fridge scan failed: {e}")


@router.post("/api/inventory/confirm_scan")
async def confirm_inventory_update(
    confirmed_data: list[ConfirmedFridgeItem],
    user_id: str = Depends(get_current_user),
):
    try:
        updated_items = []
        for item in confirmed_data:
            ingredient_id = get_or_create_ingredient(item.name)

            existing = supabase.table("inventory").select("current_quantity").eq("user_id", user_id).eq("ingredient_id", ingredient_id).limit(1).execute()

            if existing.data:
                supabase.table("inventory").update(
                    {
                        "current_quantity": item.estimated_mass,
                        "unit": item.unit,
                        "last_updated": "now()",
                    }
                ).eq("user_id", user_id).eq("ingredient_id", ingredient_id).execute()
            else:
                supabase.table("inventory").insert(
                    {
                        "user_id": user_id,
                        "ingredient_id": ingredient_id,
                        "current_quantity": item.estimated_mass,
                        "unit": item.unit,
                    }
                ).execute()

            updated_items.append(item.name)

        return {"status": "success", "synced_count": len(updated_items)}
    except Exception as e:
        logger.exception("Inventory confirmation failed")
        raise HTTPException(
            status_code=500, detail=f"Inventory confirmation failed: {e}"
        )


@router.get("/api/inventory")
async def get_inventory(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("inventory").select(
            "id, current_quantity, unit, last_updated, ingredients(name)"
        ).eq("user_id", user_id).execute()
        items = []
        for row in res.data:
            items.append({
                "id": row["id"],
                "name": row["ingredients"]["name"] if row.get("ingredients") else "Unknown",
                "quantity": row["current_quantity"],
                "unit": row["unit"],
                "last_updated": row.get("last_updated", ""),
            })
        return {"status": "success", "inventory": items}
    except Exception as e:
        logger.exception("Failed to fetch inventory")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/fridge/manual_add")
async def manual_add_ingredient(
    ingredient: ConfirmedFridgeItem,
    user_id: str = Depends(get_current_user),
):
    try:
        ingredient_id = get_or_create_ingredient(ingredient.name)

        existing = supabase.table("inventory").select("current_quantity").eq("user_id", user_id).eq("ingredient_id", ingredient_id).limit(1).execute()

        if existing.data:
            supabase.table("inventory").update(
                {
                    "current_quantity": ingredient.estimated_mass,
                    "unit": ingredient.unit,
                    "last_updated": "now()",
                }
            ).eq("user_id", user_id).eq("ingredient_id", ingredient_id).execute()
        else:
            supabase.table("inventory").insert(
                {
                    "user_id": user_id,
                    "ingredient_id": ingredient_id,
                    "current_quantity": ingredient.estimated_mass,
                    "unit": ingredient.unit,
                }
            ).execute()

        return {"status": "success", "ingredient_id": ingredient_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Manual add failed")
        raise HTTPException(status_code=500, detail=str(e))
