import os
import time
import schedule
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def check_expirations():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running Expiry Check...")
    
    # We want to flag anything expiring in the next 3 days
    threshold_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    
    # Query Supabase: Get inventory items where expiry_date <= threshold
    # The 'ingredients(name)' syntax automatically joins the tables to get the human-readable name!
    response = supabase.table('inventory').select('id, current_quantity, expiry_date, ingredients(name)').lte('expiry_date', threshold_date).execute()
    
    expiring_items = response.data
    
    if not expiring_items:
        print("   All ingredients are fresh! No notifications to send.")
        return

    for item in expiring_items:
        if not item.get('ingredients') or not item.get('expiry_date'):
            continue
            
        ing_name = item['ingredients']['name']
        
        # Calculate exactly how many days are left
        expiry_date_obj = datetime.strptime(item['expiry_date'], '%Y-%m-%d')
        days_left = (expiry_date_obj - datetime.now()).days + 1
        
        # Format the warning message
        if days_left < 0:
            status = "EXPIRED! Throw it out."
        elif days_left == 0:
            status = "Expiring TODAY! Cook it immediately."
        else:
            status = f"Expiring in {days_left} days."
            
        message = f"Heads up! You have {item['current_quantity']} units of '{ing_name}' {status}"
        print(f"   Triggering Alert: {message}")
        
        # Push the notification to the database for the UI to consume
        supabase.table('notifications').insert({'message': message}).execute()
        
    print("Check complete. Notifications saved to database.")

# ---------------------------------------------------------
# THE SCHEDULER
# In production, you would run this daily: schedule.every().day.at("09:00").do(check_expirations)
# But for local testing, let's run it every 15 seconds!
# ---------------------------------------------------------
schedule.every(15).seconds.do(check_expirations)

print("Expiry Scheduler Microservice started. Waiting for next job...")

# Keep the script running forever
try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print("\nScheduler shutting down...")