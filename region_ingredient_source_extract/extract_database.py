import os
import json
import time
import re
import requests

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

MASTER_FILE = "global_terroir_database.json"

def clean_llm_json(raw_text: str) -> str:
    """Removes markdown backticks if the model accidentally includes them."""
    cleaned = re.sub(r'^```json\s*', '', raw_text)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()

def generate_region_data(country: str, region: str) -> list:
    print(f"Querying local Ollama (qwen3:14b) for {region}, {country}...")
    
    prompt = f"""
    You are a Master Agronomist and Michelin-star sourcing expert.
    Generate a highly detailed dataset of seasonal produce (vegetables, fruits, herbs, fungi, nuts) for the specific micro-climate of '{region}' in '{country}'.
    
    CRITICAL INSTRUCTIONS:
    1. Do not list generic names. Provide specific regional varieties (e.g., 'San Marzano Tomato', 'Gariguette Strawberry').
    2. Specify the exact peak harvest months as an array of integers (e.g., [7, 8]).
    3. Include brief 'terroir_notes' explaining why this produce thrives in this soil/climate.
    
    Return EXACTLY a JSON array of objects. No markdown, no prose, just the JSON array.
    [
      {{
        "produce_name": "String (Base name)",
        "specific_variety": "String or null",
        "season_name": "String (Spring/Summer/Autumn/Winter)",
        "peak_months": [Int, Int], 
        "region": "{region}",
        "country": "{country}",
        "terroir_notes": "String"
      }}
    ]
    """
    
    try:
        # Calling local Ollama REST API
        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "qwen3:14b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json", 
                "options": {
                    "temperature": 0.3
                }
            },
            timeout=240 # High timeout since running a 14B model locally can take time per region
        )
        
        if response.status_code == 200:
            raw_output = response.json().get("message", {}).get("content", "")
            json_str = clean_llm_json(raw_output)
            return json.loads(json_str)
        else:
            print(f"Ollama API Error for {region}: {response.text}")
            return []
            
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error for {region}. Raw output was too messy: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Connection Error generating data for {region}: {e}")
        return []

def main():
    all_produce = []
    
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                # Đảm bảo chỉ lấy các item là dictionary hợp lệ
                all_produce = [item for item in content if isinstance(item, dict)]
            print(f"Loaded {len(all_produce)} valid records from {MASTER_FILE}.")
        except Exception as e:
            print(f"File database bị lỗi format, đang khởi tạo lại: {e}")
            all_produce = []

    total_regions = sum(len(regions) for regions in TARGET_ZONES.values())
    completed = 0

    for country, regions in TARGET_ZONES.items():
        for region in regions:
            # Fix lỗi AttributeError ở đây bằng cách kiểm tra type
            is_already_done = any(
                isinstance(item, dict) and item.get("region") == region 
                for item in all_produce
            )
            
            if is_already_done:
                print(f"Skipping {region}, already synthesized.")
                completed += 1
                continue
                
            region_data = generate_region_data(country, region)
            
            if region_data and isinstance(region_data, list):
                all_produce.extend(region_data)
                with open(MASTER_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_produce, f, indent=2, ensure_ascii=False)
            
            completed += 1
            print(f"Progress: {completed}/{total_regions}")
            time.sleep(1)

if __name__ == "__main__":
    main()