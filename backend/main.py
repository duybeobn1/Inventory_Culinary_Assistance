from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from config import get_settings
from db.supabase import check_supabase_connection
from db.neo4j import close_neo4j
from routers import chef, receipts, fridge, substitutions, context, auth, cook
from middleware import (
    log_requests_middleware,
    global_exception_handler,
    http_exception_handler,
)
from logging_config import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Shutting down application...")
    close_neo4j()


app = FastAPI(
    title="Culinary AI Inventory System",
    version="2.0.0",
    description="AI-powered culinary platform with TCM/Macrobiotic philosophy",
    lifespan=lifespan,
)

app.middleware("http")(log_requests_middleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(chef.router)
app.include_router(receipts.router)
app.include_router(fridge.router)
app.include_router(substitutions.router)
app.include_router(context.router)
app.include_router(auth.router)
app.include_router(cook.router)


class IngredientQuery(BaseModel):
    ingredient_name: str


@app.post("/api/v1/analyze-ingredient", tags=["AI Inference"])
async def analyze_ingredient(query: IngredientQuery):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.chef_ai_url,
                json={"ingredient": query.ingredient_name},
                timeout=45.0,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "status": "success",
                "ingredient": query.ingredient_name,
                "culinary_logic": data["analysis"],
            }
    except httpx.RequestError as e:
        logger.error(f"Chef AI Service unreachable: {e}")
        raise HTTPException(
            status_code=503, detail=f"Chef AI Service is unreachable: {e}"
        )
    except Exception as e:
        logger.exception("Unexpected error in analyze-ingredient")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {
        "status": "Serverless API is running!",
        "backend": "Modular Architecture Active",
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/health/db")
async def check_db_connection():
    connected = await check_supabase_connection()
    if connected:
        return {"status": "success", "message": "Connected to Supabase REST API"}
    return {"status": "error", "message": "Supabase connection failed"}



