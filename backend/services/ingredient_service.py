from db.supabase import supabase
from db.ai import call_chef_ai, clean_ai_json, glm_client
from logging_config import logger


def get_or_create_ingredient(raw_name: str) -> int:
    clean_name = raw_name.upper().strip()

    res = supabase.table("ingredients").select("id").ilike("name", clean_name).execute()
    if res.data:
        return res.data[0]["id"]

    thermal_prop = "Neutral"
    five_elem = "Earth"
    tastes: list[str] = []

    try:
        logger.info(f"Querying Chef AI for TCM Profile: {clean_name}")

        philosophical_text = call_chef_ai(clean_name)

        format_prompt = f"""
        Analyze this culinary philosophy text and extract the TCM properties into strict JSON.
        Text: "{philosophical_text}"

        Rules:
        1. thermal_property MUST be exactly one of: "Yin", "Yang", "Neutral".
        2. five_element MUST be exactly one of: "Wood", "Fire", "Earth", "Metal", "Water".
        3. tastes MUST be a list of strings.

        Return ONLY JSON: {{"thermal_property": "...", "five_element": "...", "tastes": [...]}}
        """

        glm_resp = glm_client.chat.completions.create(
            model="glm-4.7-flash",
            messages=[{"role": "user", "content": format_prompt}],
        )

        tcm_data = clean_ai_json(glm_resp.choices[0].message.content)
        thermal_prop = tcm_data.get("thermal_property", "Neutral")
        five_elem = tcm_data.get("five_element", "Earth")
        tastes = tcm_data.get("tastes", [])

        logger.info(f"Mapped {clean_name}: {thermal_prop} | {five_elem}")

    except Exception as e:
        logger.warning(f"Failed to get TCM data for {clean_name}: {e}. Using defaults.")

    new_res = supabase.table("ingredients").insert(
        {
            "name": clean_name,
            "category": "Uncategorized",
            "thermal_property": thermal_prop,
            "five_element": five_elem,
            "tastes": tastes,
        }
    ).execute()

    return new_res.data[0]["id"]
