from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from neo4j import GraphDatabase
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- Initialization ---
load_dotenv()
app = FastAPI()

# 1. Init Neo4j
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"), 
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

# 2. Init Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Using Flash for speed, as the graph already did the heavy logical lifting
model = genai.GenerativeModel('gemini-1.5-flash') 

# --- Data Models ---
class RecipeRequest(BaseModel):
    inventory: List[str]
    time_mode: str  # 'quick' or 'slow'

# --- The API Endpoint ---
@app.post("/api/chef/suggest")
async def suggest_recipe(request: RecipeRequest):
    # Normalize inputs to match database formatting
    normalized_ingredients = [item.lower().strip() for item in request.inventory]
    
    # STEP 1: Query Neo4j (The Graph Retrieval)
    # We look for dishes that share the most ingredients with the user's fridge
    cypher_query = """
    MATCH (d:Dish)-[:HAS_INGREDIENT]->(i:Ingredient)
    WHERE i.name IN $user_ingredients
    
    // Aggregate how many matching ingredients each dish has
    WITH d, collect(i.name) AS matched_ingredients, count(i) AS match_count
    
    // Fetch ALL ingredients for those top dishes so we know what is missing
    MATCH (d)-[:HAS_INGREDIENT]->(all_i:Ingredient)
    WITH d, matched_ingredients, match_count, collect(all_i.name) AS recipe_ingredients
    
    // Order by the most matches and get the top recommendation
    ORDER BY match_count DESC
    LIMIT 1
    
    RETURN d.name AS dish_name, 
           matched_ingredients, 
           recipe_ingredients,
           d.calories AS calories
    """
    
    with driver.session() as session:
        result = session.run(cypher_query, user_ingredients=normalized_ingredients)
        record = result.single()
        
    if not record:
        raise HTTPException(status_code=404, detail="No suitable recipes found in the graph.")

    dish_name = record["dish_name"]
    matched = record["matched_ingredients"]
    all_needed = record["recipe_ingredients"]
    
    # Calculate what the user needs to buy/substitute
    missing_ingredients = list(set(all_needed) - set(matched))

    # STEP 2: The LLM Augmentation (Gemini)
    # We strictly bound Gemini to the Graph's logic
    system_prompt = f"""
    You are a professional Michelin-trained AI chef.
    The user wants to cook: {dish_name}.
    They currently have: {', '.join(matched)}.
    They are missing: {', '.join(missing_ingredients)}.
    Their time preference is: {request.time_mode}.
    
    Task:
    Write a concise, pragmatic recipe for {dish_name} in Markdown format. 
    1. Do NOT invent new core ingredients. 
    2. If they are missing ingredients, suggest clever professional substitutions based on what they might realistically have, or tell them how to adapt the technique to cook it without them.
    3. Adapt the cooking technique to match their time preference ({request.time_mode}).
    """
    
    try:
        response = model.generate_content(system_prompt)
        return {"recipe": response.text, "graph_data_used": dish_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))