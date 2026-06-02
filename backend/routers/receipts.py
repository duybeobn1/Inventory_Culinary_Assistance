import cv2
import base64
import numpy as np
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from db.supabase import supabase
from db.ai import glm_client, clean_ai_json
from services.ingredient_service import get_or_create_ingredient
from dependencies import get_current_user
from logging_config import logger

router = APIRouter(tags=["Receipts"])


def deskew_image(image: np.ndarray) -> np.ndarray:
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

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def preprocess_receipt_image(image_bytes: bytes) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    straight_img = deskew_image(img)
    gray = cv2.cvtColor(straight_img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(
        gray, None, h=10, templateWindowSize=7, searchWindowSize=21
    )
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    _, encoded_img = cv2.imencode(".jpg", enhanced)
    return encoded_img.tobytes()


@router.post("/api/receipt/parse")
async def parse_and_sync_inventory(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    try:
        raw_image_bytes = await file.read()
        processed_image_bytes = preprocess_receipt_image(raw_image_bytes)

        prompt = """
        Analyze this receipt. Return ONLY a valid JSON.
        Instructions:
        1. Identify the receipt date ("line date" or "close date") at the top or bottom. This is the purchase date. Use it as "date".
        2. Canonicalize names to the base culinary ingredient (e.g., 'Organic Carrots 1kg' -> 'Carrot', 'Tofu Firm' -> 'Tofu'). This is CRITICAL.
        3. Mass Calculation (CRITICAL): Multiply weight by qty if both exist.
        4. Strict Units: kg, g, l, ml, or unit.
        5. Expiry Prediction: Estimate shelf life in days based on culinary standards. If a specific "best before" or "use by" date is visible on the receipt line item, calculate shelf life from the receipt date to that date.
        Format: {"vendor": "string", "date": "YYYY-MM-DD", "items": [{"name": "CLEAN_NAME", "qty": 1.0, "unit": "g", "price": 0.0, "estimated_shelf_life_days": 5}], "total": 0.0}
        """

        img_b64 = base64.b64encode(processed_image_bytes).decode("utf-8")
        response = glm_client.chat.completions.create(
            model="glm-4.6v",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
        )
        response_text = response.choices[0].message.content

        data = clean_ai_json(response_text)

        receipt_res = supabase.table("receipts").insert(
            {
                "user_id": user_id,
                "vendor": data.get("vendor"),
                "date": data.get("date"),
                "total_amount": data.get("total"),
            }
        ).execute()
        receipt_id = receipt_res.data[0]["id"]

        processed_items = []

        for item in data.get("items", []):
            ingredient_id = get_or_create_ingredient(item["name"])

            supabase.table("receipt_line").insert(
                {
                    "receipt_id": receipt_id,
                    "ingredient_id": ingredient_id,
                    "quantity": item["qty"],
                    "price": item["price"],
                }
            ).execute()

            days_to_live = item.get("estimated_shelf_life_days", 5)
            expiry_date = (
                datetime.now() + timedelta(days=days_to_live)
            ).strftime("%Y-%m-%d")

            inv_check = (
                supabase.table("inventory")
                .select("current_quantity")
                .eq("ingredient_id", ingredient_id)
                .eq("user_id", user_id)
                .execute()
            )

            if inv_check.data:
                new_qty = inv_check.data[0]["current_quantity"] + item["qty"]
                supabase.table("inventory").update(
                    {
                        "current_quantity": new_qty,
                        "expiry_date": expiry_date,
                    }
                ).eq("ingredient_id", ingredient_id).eq("user_id", user_id).execute()
            else:
                supabase.table("inventory").insert(
                    {
                        "user_id": user_id,
                        "ingredient_id": ingredient_id,
                        "current_quantity": item["qty"],
                        "unit": item.get("unit", "unit"),
                        "expiry_date": expiry_date,
                    }
                ).execute()

            processed_items.append(
                {
                    "ingredient_id": ingredient_id,
                    "name": item["name"],
                    "expires": expiry_date,
                }
            )

        return {
            "status": "success",
            "receipt_id": receipt_id,
            "items_synced": processed_items,
        }

    except Exception as e:
        logger.exception("Receipt parsing failed")
        raise HTTPException(status_code=500, detail=f"Receipt parsing failed: {e}")
