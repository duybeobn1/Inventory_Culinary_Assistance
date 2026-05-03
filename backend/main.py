from fastapi import FastAPI, UploadFile, File
import psycopg2
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

app = FastAPI(title="Culinary AI API")

# Setup Database & AI credentials
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def read_root():
    return {"status": "Serverless Backend API is running!"}

@app.get("/health/db")
def check_db():
    if not DATABASE_URL:
        return {"database": "Configuration Error: DATABASE_URL is missing"}
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return {"database": "Connected successfully to Supabase PostgreSQL!"}
    except Exception as e:
        return {"database": "Connection failed", "error": str(e)}

# --- NEW: AI Receipt Parser Endpoint ---
@app.post("/api/receipt/parse")
async def parse_receipt(file: UploadFile = File(...)):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not configured"}

    try:
        # Read the uploaded image into memory
        image_data = await file.read()
        
        # Prepare the image payload for Gemini
        image_parts = [
            {
                "mime_type": file.content_type,
                "data": image_data
            }
        ]

        # The strict Prompt to force structured JSON output
        prompt = """
        You are an expert data extraction AI. Analyze this receipt image. 
        Extract the information and return ONLY a valid JSON object without any markdown formatting or extra text.
        Structure:
        {
            "vendor": "Store Name",
            "date": "YYYY-MM-DD",
            "items": [
                {"name": "Ingredient 1", "quantity": 1, "price": 2.50},
                {"name": "Ingredient 2", "quantity": 2.5, "price": 1.20}
            ],
            "total_amount": 4.90
        }
        """

        # Call the Gemini 2.5 Flash model (Fast and cheap for OCR)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content([prompt, image_parts[0]])

        return {
            "filename": file.filename,
            "ai_extracted_json": response.text
        }

    except Exception as e:
        return {"error": str(e), "message": "Failed to process image with AI"}
