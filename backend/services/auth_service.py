from db.supabase import supabase
from logging_config import logger


def create_profile(user_id: str, display_name: str | None = None) -> dict | None:
    try:
        res = supabase.table("profiles").insert(
            {
                "user_id": user_id,
                "display_name": display_name or "Chef",
                "preferences": {},
            }
        ).execute()

        if res.data:
            logger.info(f"Profile created for user {user_id}")
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to create profile for user {user_id}: {e}")
        return None


def get_profile_by_user_id(user_id: str) -> dict | None:
    try:
        res = supabase.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Failed to get profile for user {user_id}: {e}")
        return None


def update_profile(user_id: str, updates: dict) -> dict | None:
    try:
        res = supabase.table("profiles").update(updates).eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Failed to update profile for user {user_id}: {e}")
        return None


def save_recipe(user_id: str, recipe_name: str, recipe_data: dict) -> dict | None:
    try:
        res = supabase.table("user_recipes").insert(
            {
                "user_id": user_id,
                "recipe_name": recipe_name,
                "recipe_data": recipe_data,
            }
        ).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Failed to save recipe for user {user_id}: {e}")
        return None


def get_user_recipes(user_id: str, favorites_only: bool = False) -> list:
    try:
        query = supabase.table("user_recipes").select("*").eq("user_id", user_id)
        if favorites_only:
            query = query.eq("is_favorite", True)
        res = query.order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        logger.error(f"Failed to get recipes for user {user_id}: {e}")
        return []
