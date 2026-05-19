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
            model="gemini-2.5-flash-lite",
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

    # Query Neo4j for seasonal context and molecular data (optional enhancement)
    seasonal_context = []
    molecular_context = []
    try:
        with get_neo4j_session() as session:
            # Get seasonal ingredients for current month
            current_month = datetime.now().month
            season_result = session.run(
                """
                MATCH (i:Ingredient)-[:IN_SEASON]->(s:Season)
                WHERE s.peak_months CONTAINS $month
                AND toLower(i.name) IN $user_ingredients
                RETURN i.name AS name, s.name AS season
                """,
                month=current_month,
                user_ingredients=normalized_ingredients,
            )
            for rec in season_result:
                seasonal_context.append(f"{rec['name']} is in season ({rec['season']})")

            # Get molecular compounds for ingredients
            compound_result = session.run(
                """
                MATCH (i:Ingredient)-[:HAS_COMPOUND]->(c:Compound)
                WHERE toLower(i.name) IN $user_ingredients
                RETURN i.name AS ingredient, collect(c.name) AS compounds
                LIMIT 5
                """,
                user_ingredients=normalized_ingredients,
            )
            for rec in compound_result:
                molecular_context.append(f"{rec['ingredient']}: {', '.join(rec['compounds'])}")
    except Exception as e:
        logger.warning(f"Neo4j context query failed (non-critical): {e}")

    # Build prompt for Gemini
    time_instruction = (
        "Keep the recipe under 30 minutes with simple techniques."
        if request.time_mode == "quick"
        else "Take your time with slow-cooking techniques for deeper flavors (60+ minutes)."
    )

    context_parts = []
    if seasonal_context:
        context_parts.append(f"Seasonal bonus: {'; '.join(seasonal_context)}")
    if molecular_context:
        context_parts.append(f"Flavor compounds: {'; '.join(molecular_context)}")

    system_prompt = f"""
    You are a professional Michelin-trained AI chef specializing in French technique and Eastern philosophy (Macrobiotics/TCM).

    USER'S INVENTORY:
    {', '.join(normalized_ingredients)}

    TIME CONSTRAINT:
    {time_instruction}

    ADDITIONAL CONTEXT:
    {'; '.join(context_parts) if context_parts else 'No additional context available.'}

    YOUR CORE DIRECTIVES:
    1. Create ONE complete recipe using primarily the ingredients provided (assume basic pantry items like oil, salt, pepper, water exist).
    2. PRAGMATIC SUBSTITUTIONS: If key ingredients are missing, suggest realistic pantry substitutions.
    3. TIME ADAPTATION: Strictly honor the time constraint ({request.time_mode}).
    4. PHILOSOPHICAL BALANCE: Include a short "Energetic Balance" section analyzing Yin/Yang properties and Five Elements harmony.
    5. FORMATTING: Output ONLY a clean, professional Markdown recipe with:
       - Recipe name (## heading)
       - Prep time & cook time
       - Ingredients list with quantities
       - Step-by-step instructions
       - Energetic Balance section
       No introductory filler.
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=system_prompt,
        )
        return {"recipe": response.text, "context_used": context_parts}
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
