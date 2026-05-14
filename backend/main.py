from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from database import supabase
from routers import chef, receipts, fridge, substitutions, context

app = FastAPI(title="Culinary AI Inventory System")

# Register all the modular routes
app.include_router(chef.router)
app.include_router(receipts.router)
app.include_router(fridge.router)
app.include_router(substitutions.router) 
app.include_router(context.router)

# --- CHEF AI MICROSERVICE CONFIG ---
# URL trỏ tới Inference Server (Microservice chạy Llama-3)
CHEF_AI_URL = "http://localhost:8001/generate"

class IngredientQuery(BaseModel):
    ingredient_name: str

@app.post("/api/v1/analyze-ingredient", tags=["AI Inference"])
async def analyze_ingredient(query: IngredientQuery):
    """
    Endpoint này đóng vai trò như một Proxy. Nó nhận request từ Frontend,
    sau đó gọi sang Chef AI Service (Port 8001) để xử lý logic LLM nặng, 
    rồi trả kết quả về cho user.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CHEF_AI_URL, 
                json={"ingredient": query.ingredient_name},
                timeout=45.0 # Timeout dài hơn vì LLM sinh text cần thời gian
            )
            
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "ingredient": query.ingredient_name,
                "culinary_logic": data["analysis"]
            }
        else:
            raise HTTPException(status_code=response.status_code, detail="Inference service error")
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Chef AI Service is unreachable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROOT & HEALTH CHECKS ---
@app.get("/")
def read_root():
    return {"status": "Serverless API is running!", "backend": "Modular Architecture Active"}

@app.get("/health/db")
def check_db_connection():
    try:
        res = supabase.table('ingredients').select("*").limit(1).execute()
        return {"status": "success", "message": "Connected to Supabase REST API"}
    except Exception as e: # Đã sửa lỗi typing ở đây
        return {"status": "error", "message": str(e)}