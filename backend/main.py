from fastapi import FastAPI
from database import supabase
from routers import chef, receipts, fridge, substitutions 

app = FastAPI(title="Culinary AI Inventory System")

# Register all the modular routes
app.include_router(chef.router)
app.include_router(receipts.router)
app.include_router(fridge.router)
app.include_router(substitutions.router) 

@app.get("/")
def read_root():
    return {"status": "Serverless API is running!", "backend": "Modular Architecture Active"}

@app.get("/health/db")
def check_db_connection():
    try:
        res = supabase.table('ingredients').select("*").limit(1).execute()
        return {"status": "success", "message": "Connected to Supabase REST API"}
    except Exception as e:
        return {"status": "error", "message": str(e)}