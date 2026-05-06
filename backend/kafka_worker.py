import json
import os
import time
from confluent_kafka import Consumer
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# 1. Initialize Supabase Connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Configure the Kafka Consumer
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'inventory-updater-group',  # Identifies this worker pool
    'auto.offset.reset': 'earliest'         # Read from the beginning if we missed anything
}

consumer = Consumer(conf)
consumer.subscribe(['recipe_events'])

print("🎧 Background Worker initialized. Listening for recipe events...")

try:
    while True:
        # Poll Kafka for new messages every 1 second
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print(f"❌ Consumer error: {msg.error()}")
            continue

        # 3. We caught a message! Decode the JSON payload
        event_data = json.loads(msg.value().decode('utf-8'))
        
        print(f"\n📥 INCOMING EVENT: {event_data.get('action')}")
        print(f"🍳 Dish Cooked: {event_data.get('recipe_name')}")
        
        ingredients_used = event_data.get("ingredients_used", [])
        
        # 4. Update the Supabase Inventory
        for item in ingredients_used:
            clean_item = item.lower().strip()
            print(f"   🔄 Processing used ingredient: '{clean_item}'...")
            
            # --- SUPABASE LOGIC ---
            # Step A: Look up the ingredient ID
            ing_response = supabase.table('ingredients').select('id').ilike('name', f"%{clean_item}%").execute()
            
            if ing_response.data:
                ingredient_id = ing_response.data[0]['id']
                
                # Step B: We found it! Fetch the current inventory to decrement it
                inv_response = supabase.table('inventory').select('current_quantity').eq('ingredient_id', ingredient_id).execute()
                
                if inv_response.data:
                    old_qty = inv_response.data[0]['current_quantity']
                    new_qty = max(0, old_qty - 1)  # Assuming 1 unit used for now. Prevent negative inventory.
                    
                    # Step C: Update the database
                    supabase.table('inventory').update({'current_quantity': new_qty}).eq('ingredient_id', ingredient_id).execute()
                    print(f"      ✅ Updated Supabase: {clean_item} (Qty: {old_qty} -> {new_qty})")
                else:
                    print(f"      ⚠️ '{clean_item}' is in the ingredient dictionary, but not in your fridge!")
            else:
                print(f"      ❌ '{clean_item}' not found in the database.")
                
        print("✅ Finished processing ticket.\n")

except KeyboardInterrupt:
    print("\n🛑 Worker shutting down...")
finally:
    # Always close the consumer cleanly so Kafka knows this worker disconnected
    consumer.close()