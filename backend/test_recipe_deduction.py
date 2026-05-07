import json
from database import supabase

def run_recipe_deduction_test(recipe_data):
    print(f"--- 🍳 Starting Deduction Test for: {recipe_data['recipe_name']} ---")
    
    report = []
    success = True

    for item in recipe_data['ingredients']:
        name = item['name'].upper()
        required_amount = item['amount']
        
        # 1. Fetch current inventory from Supabase
        # Assuming your table is 'inventory' and has 'ingredient_name' and 'quantity'
        res = supabase.table("inventory").select("*").eq("ingredient_name", name).execute()
        
        if not res.data:
            print(f"❌ Error: {name} not found in inventory.")
            success = False
            continue
            
        current_stock = res.data[0]['quantity']
        unit = res.data[0].get('unit', 'g')
        
        # 2. Check if enough stock exists
        if current_stock < required_amount:
            print(f"⚠️ Warning: Insufficient {name}. Need {required_amount}{unit}, have {current_stock}{unit}.")
            success = False
            continue
            
        # 3. Calculate New Quantity
        new_quantity = current_stock - required_amount
        
        # 4. Update the Database
        update_res = supabase.table("inventory")\
            .update({"quantity": new_quantity})\
            .eq("ingredient_name", name)\
            .execute()
            
        if update_res.data:
            report.append({
                "ingredient": name,
                "deducted": required_amount,
                "remaining": new_quantity,
                "status": "✅ Updated"
            })
        else:
            print(f"❌ Failed to update {name} in database.")
            success = False

    # 5. Final Report
    print("\n--- 📋 FINAL CONSUMPTION REPORT ---")
    for entry in report:
        print(f"{entry['ingredient']}: -{entry['deducted']}g | Stock: {entry['remaining']}g {entry['status']}")
    
    if success:
        print("\n✨ SUCCESS: Recipe cooked and inventory synchronized.")
    else:
        print("\n🛑 FAILURE: Some inventory updates failed or stock was low.")

if __name__ == "__main__":
    # Mock data to simulate the test
    mock_recipe = {
        "recipe_name": "Molecular Beef Stew",
        "ingredients": [
            { "name": "BEEF", "amount": 500, "unit": "g" },
            { "name": "CARROT", "amount": 200, "unit": "g" }
        ]
    }
    run_recipe_deduction_test(mock_recipe)