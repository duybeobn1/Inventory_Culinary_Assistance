import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Connect to the local Neo4j Docker container
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

# Mock FlavorDB Data
# In production, this would be a massive JSON file or API pull from a real database
mock_data = [
    {
        "ingredient": "APPLE",
        "compounds": ["Malic Acid", "Hexanal", "Ethyl Butyrate"],
        "substitutes": [{"name": "PEAR", "score": 0.85}, {"name": "PEACH", "score": 0.60}]
    },
    {
        "ingredient": "PEAR",
        "compounds": ["Malic Acid", "Hexanal", "Ethyl Decanoate"],
        "substitutes": [{"name": "APPLE", "score": 0.85}]
    },
    {
        "ingredient": "CINNAMON",
        "compounds": ["Cinnamaldehyde", "Eugenol", "Linalool"],
        "substitutes": [{"name": "NUTMEG", "score": 0.70}, {"name": "ALLSPICE", "score": 0.65}]
    },
    {
        "ingredient": "NUTMEG",
        "compounds": ["Eugenol", "Sabinene", "Myristicin"],
        "substitutes": [{"name": "CINNAMON", "score": 0.70}, {"name": "MACE", "score": 0.90}]
    }
]

def clear_database(tx):
    """Wipes the database clean before seeding."""
    tx.run("MATCH (n) DETACH DELETE n")
    print("Database cleared.")

def seed_graph(tx, data):
    """Creates nodes and relationships using Cypher queries."""
    for item in data:
        ing_name = item["ingredient"]
        
        # 1. Create the Ingredient Node
        tx.run(
            "MERGE (i:Ingredient {name: $name})",
            name=ing_name
        )
        print(f"Created Ingredient: {ing_name}")

        # 2. Create Compound Nodes and link them with HAS_COMPOUND
        for compound in item["compounds"]:
            tx.run(
                """
                MATCH (i:Ingredient {name: $ing_name})
                MERGE (c:Compound {name: $comp_name})
                MERGE (i)-[:HAS_COMPOUND]->(c)
                """,
                ing_name=ing_name, comp_name=compound
            )
            print(f"  -> Linked to Compound: {compound}")

        # 3. Create Substitution relationships
        for sub in item["substitutes"]:
            tx.run(
                """
                MATCH (i1:Ingredient {name: $ing1_name})
                MERGE (i2:Ingredient {name: $ing2_name})
                MERGE (i1)-[:IS_SUBSTITUTE_FOR {score: $score}]->(i2)
                """,
                ing1_name=ing_name, ing2_name=sub["name"], score=sub["score"]
            )
            print(f"  -> Added Substitute: {sub['name']} (Score: {sub['score']})")

if __name__ == "__main__":
    print("Connecting to Neo4j...")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            session.execute_write(clear_database)
            session.execute_write(seed_graph, mock_data)
        