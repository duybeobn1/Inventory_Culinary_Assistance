import json
from db.supabase import supabase
from db.ai import glm_client, clean_ai_json
from logging_config import logger


def extract_recipe_steps(recipe_id: str, markdown: str) -> list[dict]:
    prompt = f"""
    Parse this cooking recipe into a JSON array of sequential steps.
    For each step, estimate duration in seconds and list ingredients and tools used.

    RECIPE:
    {markdown}

    Return ONLY a JSON array with this exact schema (no markdown, no prose):
    [
      {{
        "step_number": 1,
        "instruction": "Chop the onions finely",
        "duration_seconds": 120,
        "ingredients_used": ["onion"],
        "tools_needed": ["knife", "cutting board"]
      }}
    ]

    Rules:
    - Split at logical actions (prep, cook, plate)
    - duration_seconds is your best estimate
    - ingredients_used and tools_needed should match the step
    - Return the raw array only
    """

    try:
        resp = glm_client.chat.completions.create(
            model="glm-4.7-flash",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"Step extraction AI call failed: {e}")
        return []

    try:
        steps = clean_ai_json(raw)
    except Exception as e:
        logger.warning(f"Step extraction JSON parse failed: {e}, raw: {raw[:200]}")
        return []

    if not isinstance(steps, list):
        logger.warning(f"Step extraction did not return a list: {type(steps)}")
        return []

    supabase.table("recipe_steps").delete().eq("recipe_id", recipe_id).execute()
    for step in steps:
        supabase.table("recipe_steps").insert({
            "recipe_id": recipe_id,
            "step_number": step.get("step_number", 1),
            "instruction": step.get("instruction", ""),
            "duration_seconds": step.get("duration_seconds", 0),
            "ingredients_used": json.dumps(step.get("ingredients_used", [])),
            "tools_needed": json.dumps(step.get("tools_needed", [])),
        }).execute()

    return steps


def get_recipe_steps(recipe_id: str) -> list[dict]:
    res = supabase.table("recipe_steps").select("*").eq("recipe_id", recipe_id).order("step_number").execute()
    return res.data or []


def create_session(user_id: str, recipe_id: str, background_tasks=None) -> dict | None:
    # ensure user has a profile to satisfy FK constraint
    try:
        existing = supabase.table("profiles").select("user_id").eq("user_id", user_id).execute()
        if not existing.data:
            supabase.table("profiles").insert({
                "user_id": user_id,
                "display_name": "Chef",
            }).execute()
    except Exception:
        pass

    recipe_res = supabase.table("user_recipes").select("*").eq("id", recipe_id).execute()
    if not recipe_res.data:
        return None
    recipe = recipe_res.data[0]
    recipe_name = recipe.get("recipe_name", recipe.get("name", "Untitled"))

    recipe_data = recipe.get("recipe_data", {})
    if isinstance(recipe_data, str):
        try:
            recipe_data = json.loads(recipe_data)
        except json.JSONDecodeError:
            recipe_data = {}
    markdown = recipe_data.get("recipe", "") if isinstance(recipe_data, dict) else ""

    steps = []
    try:
        steps = get_recipe_steps(recipe_id)
    except Exception:
        steps = []

    if not steps and markdown and background_tasks:
        background_tasks.add_task(extract_recipe_steps, recipe_id, markdown)

    total = len(steps) if steps else 1

    try:
        session_res = supabase.table("cooking_sessions").insert({
            "user_id": user_id,
            "recipe_id": recipe_id,
            "recipe_name": recipe_name,
            "total_steps": total,
            "current_step": 1,
            "status": "in_progress",
        }).execute()
    except Exception as e:
        return None

    if not session_res.data:
        return None

    return {
        "session_id": session_res.data[0]["id"],
        "recipe_name": recipe_name,
        "total_steps": total,
        "current_step": 1,
        "steps": steps,
    }


def get_session(session_id: str) -> dict | None:
    res = supabase.table("cooking_sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        return None
    session = res.data[0]
    try:
        step_count = len(get_recipe_steps(session.get("recipe_id", "")))
        if step_count > 0:
            session["total_steps"] = step_count
    except Exception:
        pass
    return session


def get_user_sessions(user_id: str) -> list[dict]:
    res = supabase.table("cooking_sessions").select("*").eq("user_id", user_id).in_("status", ["in_progress", "paused"]).order("last_active_at", desc=True).execute()
    return res.data or []


def advance_step(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        return {"error": "Session not found"}

    next_step = session["current_step"] + 1
    total = session["total_steps"]

    if next_step > total:
        supabase.table("cooking_sessions").update({
            "status": "completed",
            "current_step": total,
            "completed_at": "now()",
            "last_active_at": "now()",
        }).eq("id", session_id).execute()
        return {"current_step": total, "total_steps": total, "instruction": "", "session_complete": True}

    supabase.table("cooking_sessions").update({
        "current_step": next_step,
        "last_active_at": "now()",
    }).eq("id", session_id).execute()

    steps = get_recipe_steps(session["recipe_id"])
    step_instruction = ""
    for s in steps:
        if s["step_number"] == next_step:
            step_instruction = s["instruction"]
            break

    return {
        "current_step": next_step,
        "total_steps": total,
        "instruction": step_instruction,
        "session_complete": False,
    }


def pause_session(session_id: str):
    supabase.table("cooking_sessions").update({
        "status": "paused",
        "last_active_at": "now()",
    }).eq("id", session_id).execute()


def resume_session(session_id: str):
    supabase.table("cooking_sessions").update({
        "status": "in_progress",
        "last_active_at": "now()",
    }).eq("id", session_id).execute()


def abandon_session(session_id: str):
    supabase.table("cooking_sessions").update({
        "status": "abandoned",
        "last_active_at": "now()",
    }).eq("id", session_id).execute()


def process_ocr_frame(session_id: str, image_b64: str, freeform: bool = False) -> dict:
    session = get_session(session_id)
    if not session:
        return {"detected": "", "suggestion": "Session not found", "is_correct": True, "mode": "error"}

    recipe_name = session.get("recipe_name", "")
    current_step = session.get("current_step", 1)

    steps = []
    if session.get("recipe_id"):
        steps = get_recipe_steps(session["recipe_id"])

    step_instruction = ""
    for s in steps:
        if s["step_number"] == current_step:
            step_instruction = s["instruction"]
            break

    if freeform:
        prompt = f"""
        You are a cooking assistant. The user is cooking "{recipe_name}".
        Analyze this image and identify any visible ingredients, tools, or text.
        Return JSON: {{"detected": "what you see", "suggestion": "helpful hint or null"}}
        """
    else:
        prompt = f"""
        You are a cooking assistant. The user is cooking "{recipe_name}".
        Current step {current_step}: "{step_instruction}"
        Analyze this image from the user's camera. What ingredient, tool, or action do you see?
        Is the user performing the current step correctly?
        Return JSON: {{"detected": "what you see", "suggestion": "short helpful hint", "is_correct": true/false}}
        """

    try:
        resp = glm_client.chat.completions.create(
            model="glm-4.6v",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }],
        )
        raw = resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"OCR vision API call failed: {e}")
        return {
            "detected": "",
            "suggestion": "",
            "is_correct": True,
            "mode": "error",
            "error": str(e)[:200],
        }

    try:
        result = clean_ai_json(raw)
    except Exception:
        result = {"detected": raw[:200], "suggestion": "", "is_correct": True}

    result.setdefault("detected", "")
    result.setdefault("suggestion", "")
    result.setdefault("is_correct", True)
    result["mode"] = "freeform" if freeform else "step_context"
    return result
