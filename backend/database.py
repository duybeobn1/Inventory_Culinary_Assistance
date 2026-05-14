import os
import re
import json
import requests
from supabase import create_client, Client
from google import genai
from neo4j import GraphDatabase  
from dotenv import load_dotenv

load_dotenv()

# Initialize external clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Add Neo4j Connection ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
except Exception as e:
    print(f"Neo4j Warning: {e}")
    neo4j_driver = None
# -------------------------------

# --- Master Chef AI (Local Llama-3) ---
CHEF_AI_URL = "http://127.0.0.1:8001/generate"

def clean_ai_json(raw_text: str) -> dict:
    """
    The 'Nuclear Option' for cleaning AI JSON.
    Finds the first valid JSON structure and ignores all trailing garbage/prose.
    """
    start_index = -1
    for i, char in enumerate(raw_text):
        if char in ('[', '{'):
            start_index = i
            break
    
    if start_index == -1:
        raise ValueError("No JSON detected in AI response.")

    try:
        content = raw_text[start_index:]
        decoder = json.JSONDecoder()
        obj, end_pos = decoder.raw_decode(content)
        return obj
    except json.JSONDecodeError:
        match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise

def get_or_create_ingredient(raw_name: str) -> int:
    clean_name = raw_name.upper().strip()
    
    # 1. Check if ingredient already exists in Supabase
    res = supabase.table('ingredients').select('id').ilike('name', clean_name).execute()
    if len(res.data) > 0:
        return res.data[0]['id']
    
    # 2. If new, initialize default TCM attributes
    thermal_prop = "Neutral"
    five_elem = "Earth"
    tastes = []
    
    try:
        print(f"Querying Master Chef AI (Port 8001) for TCM Profile: {clean_name}")
        
        # Step A: Ask local Llama-3 for the philosophical reasoning
        llama_response = requests.post(
            CHEF_AI_URL, 
            json={"ingredient": clean_name},
            timeout=120.0 # High timeout for Mac MPS local inference
        )
        
        if llama_response.status_code == 200:
            philosophical_text = llama_response.json().get("analysis", "")
            
            # Step B: Use Gemini to strictly format Llama-3's philosophy into PostgreSQL Enums
            format_prompt = f"""
            Analyze this culinary philosophy text and extract the TCM properties into strict JSON.
            Text: "{philosophical_text}"
            
            Rules:
            1. thermal_property MUST be exactly one of: "Yin", "Yang", "Neutral".
            2. five_element MUST be exactly one of: "Wood", "Fire", "Earth", "Metal", "Water".
            3. tastes MUST be a list of strings.
            
            Return ONLY JSON: {{"thermal_property": "...", "five_element": "...", "tastes": [...]}}
            """
            
            gemini_res = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=format_prompt
            )
            
            tcm_data = clean_ai_json(gemini_res.text)
            thermal_prop = tcm_data.get("thermal_property", "Neutral")
            five_elem = tcm_data.get("five_element", "Earth")
            tastes = tcm_data.get("tastes", [])
            
            print(f"Successfully mapped {clean_name}: {thermal_prop} | {five_elem}")
        else:
            print(f"Local Chef AI returned status {llama_response.status_code}")
            
    except Exception as e:
        print(f"Failed to reach Chef AI or parse TCM data: {e}. Defaulting to Neutral/Earth.")

    # 3. Save the new ingredient with its philosophy data to Supabase
    new_res = supabase.table('ingredients').insert({
        "name": clean_name,
        "category": "Uncategorized",
        "thermal_property": thermal_prop,
        "five_element": five_elem,
        "tastes": tastes
    }).execute()
    
    return new_res.data[0]['id']