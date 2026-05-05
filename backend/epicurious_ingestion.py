import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# json files found in kaggle "https://www.kaggle.com/datasets/hugodarwood/epirecipes"
load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def ingest_recipes_in_batches(file_path, batch_size=500):
    """
    Reads the Epicurious JSON and ingests it into Neo4j in controlled batches.
    """
    print(f"Loading data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    valid_recipes = []
    for r in data:
        if isinstance(r, dict) and 'title' in r and 'ingredients' in r:
            valid_recipes.append({
                "title": r.get("title", "Unknown Dish"),
                "rating": r.get("rating", 0.0),
                "calories": r.get("calories", 0.0),
                "ingredients": r.get("ingredients", [])
            })

    total_recipes = len(valid_recipes)
    print(f"Found {total_recipes} valid recipes. Starting Graph ingestion...")

    cypher_query = """
    UNWIND $batch AS recipe
    MERGE (d:Dish {name: recipe.title})
    SET d.rating = recipe.rating,
        d.calories = recipe.calories
        
    WITH d, recipe.ingredients AS ingredients
    UNWIND ingredients AS raw_ingredient
    
    MERGE (i:Ingredient {name: toLower(trim(raw_ingredient))})
    MERGE (d)-[:HAS_INGREDIENT]->(i)
    """

    with driver.session() as session:
        for i in range(0, total_recipes, batch_size):
            batch = valid_recipes[i:i + batch_size]
            
            session.execute_write(lambda tx: tx.run(cypher_query, batch=batch))
            
            current_count = i + len(batch)
            print(f"Ingested batch {i // batch_size + 1} - ({current_count}/{total_recipes}) recipes processed.")

if __name__ == "__main__":
    json_file = "full_format_recipes.json"
    
    if os.path.exists(json_file):
        ingest_recipes_in_batches(json_file)
        print("Data ingestion complete.")
    else:
        print(f"Error: {json_file} not found in the current directory.")
        
    driver.close()