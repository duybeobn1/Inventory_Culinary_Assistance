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


def save_recipe(user_id: str, recipe_name: str, recipe_data: dict, is_favorite: bool = False) -> dict | None:
    try:
        existing = supabase.table("user_recipes").select("id").eq("user_id", user_id).eq("recipe_name", recipe_name).execute()
        if existing.data and len(existing.data) > 0:
            return existing.data[0]

        res = supabase.table("user_recipes").insert(
            {
                "user_id": user_id,
                "recipe_name": recipe_name,
                "recipe_data": recipe_data,
                "is_favorite": is_favorite,
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


def update_recipe(recipe_id: str, user_id: str, **kwargs) -> dict | None:
    try:
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return None
        res = (
            supabase.table("user_recipes")
            .update(update_data)
            .eq("id", recipe_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"Failed to update recipe {recipe_id}: {e}")
        return None


def delete_recipe(recipe_id: str, user_id: str) -> bool:
    try:
        supabase.table("user_recipes").delete().eq("id", recipe_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete recipe {recipe_id}: {e}")
        return False
