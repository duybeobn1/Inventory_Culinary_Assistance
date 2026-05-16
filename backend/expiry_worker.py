import os
import time
import schedule
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from config import get_settings
from logging_config import logger

load_dotenv()
settings = get_settings()

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


def check_expirations():
    logger.info("Running expiry check...")

    threshold_date = (
        datetime.now() + timedelta(days=settings.expiry_check_days)
    ).strftime("%Y-%m-%d")

    response = (
        supabase.table("inventory")
        .select("id, user_id, current_quantity, expiry_date, ingredients(name)")
        .lte("expiry_date", threshold_date)
        .execute()
    )

    expiring_items = response.data

    if not expiring_items:
        logger.info("All ingredients are fresh. No notifications needed.")
        return

    for item in expiring_items:
        if not item.get("ingredients") or not item.get("expiry_date"):
            continue

        ing_name = item["ingredients"]["name"]
        user_id = item.get("user_id")
        expiry_date_obj = datetime.strptime(item["expiry_date"], "%Y-%m-%d")
        days_left = (expiry_date_obj - datetime.now()).days + 1

        if days_left < 0:
            status = "EXPIRED! Throw it out."
        elif days_left == 0:
            status = "Expiring TODAY! Cook it immediately."
        else:
            status = f"Expiring in {days_left} days."

        message = f"Heads up! You have {item['current_quantity']} units of '{ing_name}' {status}"
        logger.info(f"Triggering alert for user {user_id}: {message}")

        notification_data = {"message": message}
        if user_id:
            notification_data["user_id"] = user_id
        supabase.table("notifications").insert(notification_data).execute()

    logger.info("Expiry check complete. Notifications saved.")


schedule.every(15).seconds.do(check_expirations)

logger.info("Expiry Scheduler Microservice started. Waiting for next job...")

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Scheduler shutting down...")
