from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from db.neo4j import get_neo4j_session, neo4j_driver
from db.ai import ai_client, clean_ai_json, call_chef_ai, call_ollama
from services.ingredient_service import get_or_create_ingredient
from kafka_client import publish_event
from routers.context import determine_season, evaluate_tcm_weather_balance
from logging_config import logger

router = APIRouter(tags=["Chef & Recipe Generation"])


class IngredientQuery(BaseModel):
    ingredient_name: str


class MenuRequest(BaseModel):
    inventory: List[str]
    latitude: float
    longitude: float


class RecipeRequest(BaseModel):
    inventory: List[str]
    time_mode: str


class CookRecipeRequest(BaseModel):
    recipe_name: str
    ingredients_used: List[str]


@router.post("/api/chef/analyze-ingredient")
async def analyze_ingredient(query: IngredientQuery):
    try:
        analysis = await call_chef_ai(query.ingredient_name)
        return {
            "status": "success",
            "ingredient": query.ingredient_name,
            "culinary_logic": analysis,
        }
    except Exception as e:
        logger.error(f"Chef AI analysis failed for {query.ingredient_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Chef AI Service unavailable: {e}",
        )


@router.post("/api/chef/generate-menu")
async def generate_balanced_menu(request: MenuRequest):
    normalized_ingredients = [item.lower().strip() for item in request.inventory]
    current_month = datetime.now().month
    season = determine_season(request.latitude, current_month)

    temp_c = 15.0
    precipitation = 1.2

    tcm_context = evaluate_tcm_weather_balance(temp_c, precipitation, season)
    target_energy = tcm_context["target_thermal_property"]

    logger.info(f"Generating {target_energy}-focused menu for season: {season}")

    ollama_prompt = f"""
    You are a Master Michelin-Star Chef and expert in Traditional Chinese Medicine (TCM) dietary therapy.

    ENVIRONMENT:
    - Season: {season}
    - Weather: {temp_c} degrees Celsius, Precipitation: {precipitation}mm
    - TCM Diagnosis: {tcm_context['environmental_energy']}. {tcm_context['dietary_suggestion']}

    INVENTORY:
    {', '.join(normalized_ingredients)}

    TASK:
    Design a balanced 3-course menu (Starter, Main Course, Side/Dessert) using ONLY the inventory provided (assume basic pantry items like oil, salt, and water exist).

    RULES:
    1. Energetic Balance: The overall menu must lean toward '{target_energy}' to balance the current weather.
    2. Internal Harmony: If the Main Course is heavily Yang (warming/spicy), the Starter or Side MUST be Yin (cooling) to prevent overheating.
    3. Explain the TCM synergy and why these specific ingredients were chosen together.
    """

    try:
        philosophical_raw_text = await call_ollama(ollama_prompt)
    except Exception as e:
        logger.exception("Ollama menu generation failed")
        raise

    formatting_prompt = f"""
    You are a strict data formatter. Extract the 3-course menu and TCM philosophy from the following text into a structured JSON array.

    RAW TEXT:
    {philosophical_raw_text}

    REQUIREMENTS:
    Return EXACTLY a JSON array of objects representing the courses. Do NOT include markdown blocks.

    SCHEMA:
    [
      {{
        "course_type": "Starter | Main | Side | Dessert",
        "dish_name": "String",
        "ingredients_used": ["String", "String"],
        "thermal_property": "Yin | Yang | Neutral",
        "tcm_reasoning": "1-2 sentences explaining why this dish balances the menu or environment."
      }}
    ]
    """

    try:
        gemini_response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatting_prompt,
        )

        raw_output = gemini_response.text
        cleaned_json = raw_output.replace("```json", "").replace("```", "").strip()
        menu_json = clean_ai_json(cleaned_json)

        return {
            "status": "success",
            "environmental_target": target_energy,
            "menu": menu_json,
        }
    except Exception as e:
        logger.exception("Gemini menu formatting failed")
        raise


@router.post("/api/chef/suggest")
async def suggest_recipe(request: RecipeRequest):
    normalized_ingredients = [item.lower().strip() for item in request.inventory]

    cypher_query = """
        MATCH (d:Dish)
        WHERE NOT d.name =~ '(?i).*(stock|broth|sauce|dough|marinade|dressing|syrup|spice rub|chutney|jam|relish|dip|salsa).*'

        MATCH (d)-[:HAS_INGREDIENT]->(i:Ingredient)
        WITH d, collect(DISTINCT i.name) AS recipe_ingredients

        WITH d, recipe_ingredients,
            [user_ing IN $user_ingredients WHERE ANY(ri IN recipe_ingredients WHERE
                ri =~ '(?i).*\\b' + user_ing + '\\b.*'
                AND NOT ri =~ '(?i).*(broth|stock|bouillon|water|juice).*'
            )] AS matched_user_ingredients

        WHERE size(matched_user_ingredients) > 0

        ORDER BY size(matched_user_ingredients) DESC, size(recipe_ingredients) ASC
        LIMIT 1

        RETURN d.name AS dish_name,
            matched_user_ingredients AS matched_ingredients,
            recipe_ingredients,
            d.calories AS calories
        """

    with get_neo4j_session() as session:
        result = session.run(cypher_query, user_ingredients=normalized_ingredients)
        record = result.single()

    if not record:
        raise ValueError("No suitable recipes found in the graph.")

    dish_name = record["dish_name"]
    matched = record["matched_ingredients"]
    all_needed = record["recipe_ingredients"]
    missing_ingredients = list(set(all_needed) - set(matched))

    system_prompt = f"""
    You are a professional Michelin-trained AI chef specializing in French technique and Eastern philosophy (Macrobiotics/TCM).
    The user is looking to cook a substantial, satisfying meal.

    DATABASE RETRIEVAL:
    - Target Dish: {dish_name}
    - User has: {', '.join(matched)}
    - User is missing: {', '.join(missing_ingredients)}
    - Time constraint: {request.time_mode}

    YOUR CORE DIRECTIVES:
    1. MEAL INTEGRITY: If "{dish_name}" is historically a side dish or condiment, elevate it into a main course naturally.
    2. PRAGMATIC SUBSTITUTIONS: Provide realistic substitutions for missing ingredients using common pantry staples.
    3. TIME ADAPTATION: Adapt the cooking technique to strictly honor their time constraint ({request.time_mode}).
    4. PHILOSOPHICAL BALANCE (CRITICAL): Include a short "Energetic Balance" section. Briefly analyze the Yin (cooling) and Yang (warming) properties of the main ingredients, and suggest how the chosen cooking technique (e.g., high heat vs. slow simmer) brings the dish into harmony based on the Five Elements.
    5. FORMATTING: Output ONLY a clean, professional Markdown recipe. No introductory filler.
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=system_prompt,
        )
        return {"recipe": response.text, "graph_data_used": dish_name}
    except Exception as e:
        logger.exception("Recipe suggestion generation failed")
        raise


@router.post("/api/chef/cook")
async def cook_recipe(request: CookRecipeRequest):
    event_payload = {
        "action": "recipe_completed",
        "recipe_name": request.recipe_name,
        "ingredients_used": request.ingredients_used,
    }

    try:
        publish_event(topic="recipe_events", event_data=event_payload)
    except Exception as e:
        logger.exception("Kafka publish failed")
        raise

    return {
        "status": "success",
        "message": f"'{request.recipe_name}' logged. Inventory updating in background.",
    }
