import json
import os
import time
from confluent_kafka import Consumer
from supabase import create_client, Client
from dotenv import load_dotenv
from logging_config import logger

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

conf = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "inventory-updater-group",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(conf)
consumer.subscribe(["recipe_events"])

logger.info("Background Worker initialized. Listening for recipe events...")

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue

        event_data = json.loads(msg.value().decode("utf-8"))

        logger.info(f"Incoming event: {event_data.get('action')}")
        logger.info(f"Dish cooked: {event_data.get('recipe_name')}")

        ingredients_used = event_data.get("ingredients_used", [])

        for item in ingredients_used:
            clean_item = item.lower().strip()
            logger.info(f"Processing used ingredient: '{clean_item}'...")

            ing_response = (
                supabase.table("ingredients")
                .select("id")
                .ilike("name", f"%{clean_item}%")
                .execute()
            )

            if ing_response.data:
                ingredient_id = ing_response.data[0]["id"]

                inv_response = (
                    supabase.table("inventory")
                    .select("current_quantity")
                    .eq("ingredient_id", ingredient_id)
                    .execute()
                )

                if inv_response.data:
                    old_qty = inv_response.data[0]["current_quantity"]
                    new_qty = max(0, old_qty - 1)

                    supabase.table("inventory").update(
                        {"current_quantity": new_qty}
                    ).eq("ingredient_id", ingredient_id).execute()
                    logger.info(f"Updated: {clean_item} (Qty: {old_qty} -> {new_qty})")
                else:
                    logger.warning(f"'{clean_item}' in dictionary but not in inventory")
            else:
                logger.warning(f"'{clean_item}' not found in database")

        logger.info("Finished processing event.\n")

except KeyboardInterrupt:
    logger.info("Worker shutting down...")
finally:
    consumer.close()
    logger.info("Consumer closed")
