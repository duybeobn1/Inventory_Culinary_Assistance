from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import httpx

router = APIRouter(tags=["Environmental Context"])

# Open-Meteo API requires no authentication and is completely free
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

def determine_season(latitude: float, month: int) -> str:
    """Calculates the current season based on hemisphere and month."""
    is_northern = latitude >= 0
    
    if month in [3, 4, 5]:
        return "Spring" if is_northern else "Autumn"
    elif month in [6, 7, 8]:
        return "Summer" if is_northern else "Winter"
    elif month in [9, 10, 11]:
        return "Autumn" if is_northern else "Spring"
    else:
        return "Winter" if is_northern else "Summer"

def evaluate_tcm_weather_balance(temp_c: float, precipitation: float, season: str) -> dict:
    """
    Translates physical weather data into Macrobiotic / TCM philosophy.
    Recommends dietary balances based on the external environment.
    """
    recommendation = {
        "environmental_energy": "Neutral",
        "dietary_suggestion": "Maintain a balanced intake of Yin and Yang.",
        "target_thermal_property": "Neutral"
    }

    if temp_c > 28.0:
        recommendation["environmental_energy"] = "Excessive Yang (Hot)"
        recommendation["dietary_suggestion"] = "The environment is very hot. Incorporate cooling (Yin) foods like cucumber, tofu, and raw salads to clear internal heat."
        recommendation["target_thermal_property"] = "Yin"
    elif temp_c < 10.0:
        recommendation["environmental_energy"] = "Excessive Yin (Cold)"
        recommendation["dietary_suggestion"] = "The environment is cold. Focus on warming (Yang) foods like ginger, lamb, and slow-cooked stews to build internal heat."
        recommendation["target_thermal_property"] = "Yang"
    elif precipitation > 0.5:
        recommendation["environmental_energy"] = "Dampness"
        recommendation["dietary_suggestion"] = "The weather is rainy and damp. Avoid heavy dairy and sugar; favor aromatic, moisture-draining ingredients like barley and radishes."
        recommendation["target_thermal_property"] = "Yang"
        
    return recommendation

@router.get("/api/context/environment")
async def get_environmental_context(
    lat: float = Query(..., description="Latitude of the user"),
    lon: float = Query(..., description="Longitude of the user")
):
    """
    Fetches real-time weather and season data, then provides philosophical 
    dietary parameters for the Chef AI to use in menu planning.
    """
    try:
        # Fetch current temperature and precipitation
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation",
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(WEATHER_API_URL, params=params, timeout=10.0)
            
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Weather service unavailable.")
            
        data = response.json()
        current_data = data.get("current", {})
        
        temp_c = current_data.get("temperature_2m", 20.0)
        precipitation = current_data.get("precipitation", 0.0)
        
        # Calculate Season
        current_month = datetime.now().month
        season = determine_season(lat, current_month)
        
        # Calculate Philosophical Balance
        tcm_advice = evaluate_tcm_weather_balance(temp_c, precipitation, season)
        
        return {
            "status": "success",
            "location": {"latitude": lat, "longitude": lon},
            "weather": {
                "temperature_celsius": temp_c,
                "is_raining": precipitation > 0,
                "season": season
            },
            "macrobiotic_context": tcm_advice
        }
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to connect to weather API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))