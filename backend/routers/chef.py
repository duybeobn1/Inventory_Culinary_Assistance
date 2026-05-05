from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from neo4j import GraphDatabase
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"), 
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class RecipeRequest(BaseModel):
    inventory: List[str]
    time_mode: str  

@router.post("/api/chef/suggest")
async def suggest_recipe(request: RecipeRequest):
    normalized_ingredients = [item.lower().strip() for item in request.inventory]
    
    # 1. UPGRADED GRAPH QUERY (Strict Word Boundaries & Broader Blacklist)
    cypher_query = """
        // 1. Filter out condiments and base components immediately
        MATCH (d:Dish)
        WHERE NOT d.name =~ '(?i).*(stock|broth|sauce|dough|marinade|dressing|syrup|spice rub|chutney|jam|relish|dip|salsa).*'
        
        // 2. Gather all ingredients for valid dishes
        MATCH (d)-[:HAS_INGREDIENT]->(i:Ingredient)
        WITH d, collect(DISTINCT i.name) AS recipe_ingredients
        
        // 3. THE FIX: Loop through the USER'S list. Count it as a match only once per user ingredient.
        WITH d, recipe_ingredients,
            [user_ing IN $user_ingredients WHERE ANY(ri IN recipe_ingredients WHERE 
                ri =~ '(?i).*\\\\b' + user_ing + '\\\\b.*' 
                AND NOT ri =~ '(?i).*(broth|stock|bouillon|water|juice).*'
            )] AS matched_user_ingredients
        
        // 4. Ensure it matched at least something
        WHERE size(matched_user_ingredients) > 0
        
        // 5. Order by highest number of USER ingredients matched, then by simplest recipe
        ORDER BY size(matched_user_ingredients) DESC, size(recipe_ingredients) ASC
        LIMIT 1
        
        RETURN d.name AS dish_name, 
            matched_user_ingredients AS matched_ingredients, 
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
    missing_ingredients = list(set(all_needed) - set(matched))

    # 2. UPGRADED LLM PROMPT (Adding Guardrails and Contextual Reasoning)
    system_prompt = f"""
    You are a professional Michelin-trained AI chef.
    The user is looking to cook a substantial, satisfying meal.
    
    DATABASE RETRIEVAL:
    - Target Dish: {dish_name}
    - User has: {', '.join(matched)}
    - User is missing: {', '.join(missing_ingredients)}
    - Time constraint: {request.time_mode}
    
    YOUR CORE DIRECTIVES:
    1. MEAL INTEGRITY: The user wants a main course. If "{dish_name}" is historically a side dish, condiment, or appetizer, you MUST elevate it into a main course by naturally incorporating their available ingredients (e.g., serving the chutney over seared beef).
    2. PRAGMATIC SUBSTITUTIONS: If they are missing ingredients, do not just list what is missing. Provide realistic, immediate substitutions using common pantry staples, or explain how to skip it without ruining the dish.
    3. TIME ADAPTATION: Radically adapt the cooking technique to strictly honor their time constraint ({request.time_mode}). If it's "quick", use high heat, smaller cuts of meat, or skip long marinades.
    4. FORMATTING: Output ONLY a clean, professional Markdown recipe. No introductory conversational filler.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=system_prompt,
        )
        return {"recipe": response.text, "graph_data_used": dish_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))