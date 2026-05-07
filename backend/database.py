import os
import re
import json
from supabase import create_client, Client
from google import genai
from neo4j import GraphDatabase  # <-- 1. Add this import
from dotenv import load_dotenv

load_dotenv()

# Initialize external clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- 2. Add Neo4j Connection ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
except Exception as e:
    print(f"⚠️ Neo4j Warning: {e}")
    neo4j_driver = None
# -------------------------------

def clean_ai_json(raw_text: str) -> dict:
    """
    The 'Nuclear Option' for cleaning AI JSON.
    Finds the first valid JSON structure and ignores all trailing garbage/prose.
    """
    # Find the start of the JSON (first [ or {)
    start_index = -1
    for i, char in enumerate(raw_text):
        if char in ('[', '{'):
            start_index = i
            break
    
    if start_index == -1:
        raise ValueError("No JSON detected in AI response.")

    # Use the raw_decode method to stop exactly where the JSON ends
    try:
        content = raw_text[start_index:]
        decoder = json.JSONDecoder()
        obj, end_pos = decoder.raw_decode(content)
        return obj
    except json.JSONDecodeError:
        # Fallback to a desperate regex if the decoder fails
        match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise

def get_or_create_ingredient(raw_name: str) -> int:
    res = supabase.table('ingredients').select('id').ilike('name', raw_name).execute()
    if len(res.data) > 0:
        return res.data[0]['id']
    
    new_res = supabase.table('ingredients').insert({
        "name": raw_name.upper(),
        "category": "Uncategorized"
    }).execute()
    return new_res.data[0]['id']