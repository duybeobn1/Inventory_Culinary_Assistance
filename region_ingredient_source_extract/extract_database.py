import os
import json
import time
import re
import requests
from zai import ZaiClient
from dotenv import load_dotenv

load_dotenv()

# Initialize Zhipu AI Client
client = ZaiClient(api_key=os.getenv("ZHIPUAI_API_KEY"))

# MASSIVE GLOBAL TERROIR MATRIX (10+ Regions per Country)
TARGET_ZONES = {
    "France": [
        "Île-de-France (Urban/Temperate)", 
        "Provence (Dry Mediterranean)", 
        "Côte d'Azur (Coastal Mediterranean)",
        "Bretagne (Oceanic/Coastal)", 
        "Normandie (Cool Oceanic)",
        "Nouvelle-Aquitaine (Warm Oceanic/Bordeaux)", 
        "Auvergne-Rhône-Alpes (Alpine/Continental)", 
        "Bourgogne-Franche-Comté (Continental)",
        "Occitanie (Southern/Pyrenees)",
        "Hauts-de-France (Northern/Cool)",
        "Grand Est (Alsace/Champagne - Continental)",
        "Corse (Island Mediterranean)"
    ],
    "Italy": [
        "Piedmont (Alpine/Continental)", 
        "Lombardy (Lakes/Plains)", 
        "Veneto (Coastal/Lagoon)", 
        "Trentino-Alto Adige (High Alpine)",
        "Emilia-Romagna (Po Valley/Fertile)", 
        "Tuscany (Hilly Mediterranean)", 
        "Umbria (Landlocked/Hilly)",
        "Lazio (Volcanic Soils/Coastal)",
        "Campania (Volcanic/Warm)", 
        "Puglia (Hot/Dry/Limestone)",
        "Sicily (Warm Island/Arid)", 
        "Sardinia (Island/Windy)"
    ],
    "Spain": [
        "Andalusia (Hot/Dry Mediterranean)", 
        "Catalonia (Coastal/Mountainous)", 
        "Galicia (Wet Oceanic)", 
        "Basque Country (Cool/Humid)",
        "Valencia (Warm Coastal Mediterranean)", 
        "Castile and León (High Plateau/Extreme Temps)",
        "Castile-La Mancha (Dry Plains)",
        "Extremadura (Arid/Dehesa)",
        "Aragon (Ebro Valley/Pyrenees)",
        "Canary Islands (Volcanic Subtropical)",
        "Balearic Islands (Mediterranean)"
    ],
    "Japan": [
        "Hokkaido (Subarctic/Harsh Winters)", 
        "Aomori (Cool Temperate/Orchards)",
        "Tohoku (Snow Country)", 
        "Kanto (Temperate Plain)", 
        "Chubu (Japanese Alps/High Altitude)",
        "Hokuriku (Sea of Japan/Heavy Snow)",
        "Kansai (Warm Temperate)", 
        "Chugoku (Inland Sea/Mild)",
        "Shikoku (Warm/Citrus Heavy)",
        "Kyushu (Subtropical/Volcanic)", 
        "Okinawa (Tropical Island)"
    ],
    "USA": [
        "Northern California (Cool Coastal/Fog)", 
        "Central Valley CA (Hot/Dry Agricultural)", 
        "Southern California (Desert/Mediterranean)",
        "Pacific Northwest (Humid/Temperate)", 
        "Desert Southwest (Arid/Hot)",
        "Rocky Mountains (High Altitude)",
        "Midwest/Great Plains (Continental/Fertile)",
        "Deep South (Subtropical/Humid)",
        "Florida (Tropical/Subtropical)",
        "Mid-Atlantic (Temperate/Coastal)",
        "New England (Distinct 4 Seasons/Cold Winters)"
    ],
    "China": [
        "Sichuan Basin (Humid/Cloudy)", 
        "Yunnan Plateau (Diverse/High Altitude)", 
        "Guangdong (Subtropical Coastal)", 
        "Shandong (Temperate Peninsula)", 
        "Xinjiang (Arid/Desert/Extreme)", 
        "Heilongjiang (Frigid/Short Season)", 
        "Zhejiang (Humid Subtropical)", 
        "Fujian (Mountainous Coastal)", 
        "Hainan (Tropical Island)", 
        "Inner Mongolia (Grassland/Steppe)"
    ],
    "Vietnam": [
        "Northwest High Mountains (Sapa/Lai Chau)", 
        "Northeast Limestone (Ha Giang)", 
        "Red River Delta (Hanoi/Fertile)", 
        "North Central Coast (Thanh Hoa/Harsh Weather)", 
        "Mid Central Coast (Hue/Da Nang)", 
        "South Central Coast (Nha Trang/Dry)", 
        "Northern Central Highlands (Kon Tum)", 
        "Southern Central Highlands (Da Lat/Temperate)", 
        "Mekong Delta (Can Tho/Humid Tropical)", 
        "Tropical Islands (Phu Quoc)"
    ],
    "Mexico": [
        "Baja California (Desert/Mediterranean)",
        "Sonoran Desert (Arid/Extreme Heat)",
        "Sinaloa (Coastal Agricultural)",
        "Jalisco (Central Highlands)",
        "Michoacán (Volcanic/Temperate)",
        "Oaxaca (Mountainous/Complex Microclimates)",
        "Chiapas (Highland Jungles)",
        "Veracruz (Humid Gulf Coast)",
        "Yucatan Peninsula (Tropical/Limestone)",
        "Central Valleys (High Altitude/Dry)"
    ]
}

MASTER_FILE = "global_terroir_hierarchical.json"

def clean_llm_json(raw_text: str) -> str:
    """Removes markdown backticks if GLM-4 accidentally includes them."""
    cleaned = re.sub(r'^```json\s*', '', raw_text)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()

def generate_region_data(country: str, region: str) -> dict:
    print(f"Synthesizing hierarchical seasonal data for {region}, {country}...")
    
    prompt = f"""
    You are a Master Agronomist and Michelin-star sourcing expert. 
    Generate a deep seasonal produce database for '{region}' in '{country}'.

    OUTPUT STRUCTURE:
    Return a single JSON object where the keys are exactly: "Spring", "Summer", "Autumn", "Winter".
    
    CRITICAL CONSTRAINT:
    Each season MUST contain an array of AT LEAST 8 unique, diverse ingredients (vegetables, fruits, herbs, or fungi).
    
    DATA FIELDS PER INGREDIENT:
    - produce_name: Common English name.
    - specific_variety: The specific regional cultivar (e.g., 'Mara des Bois Strawberry') or null.
    - peak_months: List of integers (e.g., [5, 6]).
    - terroir_notes: One specific sentence on why this variety thrives in {region}.

    Return ONLY the raw JSON object. No markdown, no prose.
    """
    
    try:
        response = client.chat.completions.create(
            model="glm-4.7-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        raw_output = response.choices[0].message.content
        json_str = clean_llm_json(raw_output)
        return json.loads(json_str)
        
    except Exception as e:
        print(f"Error generating data for {region}: {e}")
        return None

def main():
    master_db = {}
    
    # Load existing progress to allow resuming
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            try:
                master_db = json.load(f)
                print(f"Resuming: Loaded data for {len(master_db)} countries.")
            except json.JSONDecodeError:
                master_db = {}

    for country, regions in TARGET_ZONES.items():
        if country not in master_db:
            master_db[country] = {}
            
        for region in regions:
            if region in master_db[country]:
                print(f"Skipping {region}, already processed.")
                continue
                
            region_data = generate_region_data(country, region)
            
            if region_data:
                master_db[country][region] = region_data
                # Save after every region to prevent data loss
                with open(MASTER_FILE, "w", encoding="utf-8") as f:
                    json.dump(master_db, f, indent=2, ensure_ascii=False)
            
            # GLM-4-Flash is fast; a small sleep helps avoid API bursts
            time.sleep(1) 

    print(f"Data synthesis complete. Hierarchical database saved to {MASTER_FILE}")

if __name__ == "__main__":
    main()