from supabase import create_client, Client
from config import get_settings
from logging_config import logger

settings = get_settings()

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


async def check_supabase_connection() -> bool:
    try:
        res = supabase.table("ingredients").select("*").limit(1).execute()
        return res.data is not None
    except Exception as e:
        logger.error(f"Supabase connection check failed: {e}")
        return False


def get_authenticated_user(token: str) -> dict | None:
    try:
        user = supabase.auth.get_user(token)
        return user.user.model_dump() if hasattr(user, "user") else None
    except Exception as e:
        logger.warning(f"Supabase auth verification failed: {e}")
        return None
