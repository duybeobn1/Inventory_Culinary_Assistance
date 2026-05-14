from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database import neo4j_driver, ai_client, clean_ai_json, supabase

router = APIRouter(tags=["Flavor Matrix & Philosophy"])

# --- ENGINE 1: MOLECULAR GRAPH (NEO4J) ---

def save_ai_substitutes_to_graph(target_ingredient: str, substitutes_list: list):
    """
    Performs a Dual-Link Graph Update. 
    Connects BOTH the target and the substitute ingredients to the discovered 
    chemical compounds, enriching the graph density with every search.
    """
    query = """
    // 1. Anchor the target ingredient
    MERGE (target:Ingredient {name: toUpper($target_name)})
    
    WITH target
    UNWIND $subs AS sub
    
    // 2. Anchor the substitute ingredient node
    MERGE (sub_node:Ingredient {name: toUpper(sub.ingredient)})
    
    // 3. Create/Update the substitution relationship
    MERGE (target)-[r:IS_SUBSTITUTE_FOR]->(sub_node)
    SET r.score = COALESCE(sub.overall_score, 0.0),
        r.flavor_score = COALESCE(sub.flavor_score, 0.0),
        r.ai_generated = true
        
    // 4. Molecular Enrichment: Link BOTH nodes to the compounds
    WITH target, sub_node, sub.shared_compounds AS compounds
    UNWIND compounds AS comp_name
    
    MERGE (c:Compound {name: toUpper(comp_name)})
    
    // Draw links from both sides to ensure the substitute also learns its chemistry
    MERGE (target)-[:HAS_COMPOUND {ai_generated: true}]->(c)
    MERGE (sub_node)-[:HAS_COMPOUND {ai_generated: true}]->(c)
    """
    
    try:
        with neo4j_driver.session() as session:
            session.run(query, target_name=target_ingredient, subs=substitutes_list)
            print(f"Molecular Graph Deep-Linked: Learned chemicals for {target_ingredient} and its matches.")
    except Exception as e:
        print(f"Failed to save molecular data to graph: {e}")

@router.get("/api/substitute/molecular/{ingredient_name}")
async def get_molecular_substitutes(
    ingredient_name: str, 
    restriction: Optional[str] = Query(None, description="e.g., Vegan, Nut-Free, Keto"),
    recipe_context: Optional[str] = Query(None, description="e.g., Baking a cake, making a soup, raw salad")
):
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j database is not connected.")

    # STEP 1: Extract Molecular Profile from Graph (RAG Context)
    chemistry_query = "MATCH (target:Ingredient {name: toUpper($name)})-[:HAS_COMPOUND]->(c:Compound) RETURN collect(c.name) AS compounds"
    known_compounds = []
    try:
        with neo4j_driver.session() as session:
            chem_result = session.run(chemistry_query, name=ingredient_name)
            record = chem_result.single()
            if record and record["compounds"]:
                known_compounds = record["compounds"]
    except Exception as e:
        print(f"Chemistry extraction failed: {e}")

    # STEP 2: Pure Graph Query (Only if no situational context is needed)
    if not restriction and not recipe_context and known_compounds:
        sub_query = """
        MATCH (target:Ingredient {name: toUpper($name)})-[:HAS_COMPOUND]->(c:Compound)<-[:HAS_COMPOUND]-(sub:Ingredient)
        WITH target, sub, COUNT(c) AS shared_compounds_count
        OPTIONAL MATCH (target)-[r:IS_SUBSTITUTE_FOR]->(sub)
        RETURN sub.name AS substitute, shared_compounds_count AS shared_compounds, COALESCE(r.score, 0) AS explicit_score
        ORDER BY shared_compounds DESC, explicit_score DESC
        LIMIT 5
        """
        try:
            with neo4j_driver.session() as session:
                result = session.run(sub_query, name=ingredient_name)
                substitutes = [{"ingredient": rec["substitute"], "shared_flavor_compounds": rec["shared_compounds"], "overall_score": rec["explicit_score"]} for rec in result]
                
            if substitutes:
                return {
                    "status": "success", 
                    "source": "neo4j_graph",
                    "target_ingredient": ingredient_name.upper(), 
                    "substitutes": substitutes
                }
        except Exception as e:
            pass 

    # STEP 3: The Deep-Enrichment RAG Prompt
    print(f"Triggering Molecular AI for [{ingredient_name}] | Diet: {restriction} | Context: {recipe_context}")
    
    chem_context = f"Known markers for target: {', '.join(known_compounds)}" if known_compounds else "No base chemistry known. Perform molecular synthesis."
    diet_context = f"DIET CONSTRAINT: Must be {restriction}." if restriction else "No dietary restrictions."
    usage_context = f"FUNCTIONAL CONTEXT: Functioning for '{recipe_context}'." if recipe_context else "General culinary utility."

    fallback_prompt = f"""
    Role: Senior Molecular Gastronomist & Flavor Chemist API.
    Task: Provide exactly 5 ingredient substitutes for '{ingredient_name}' and map their defining chemical signatures.

    Context:
    - {chem_context}
    - {diet_context}
    - {usage_context}

    Strict Constraints (FAILURE TO FOLLOW RESULTS IN SYSTEM ERROR):
    1. ARRAY ENFORCEMENT: You MUST return a JSON ARRAY [ ], even if there is only one result.
    2. ONLY JSON: Return ONLY a raw, minified JSON array. Do NOT include any conversational text, 'Certainly!', or markdown (no ```json blocks).
    3. MOLECULAR MAPPING: The 'shared_compounds' array MUST contain the scientific names of 3-5 primary chemical flavor markers (e.g., "Piperine", "1-Octen-3-one") that define the essence of BOTH the target and the substitute.
    4. COMPLIANCE: If a substitute violates the diet constraint ({restriction}), it must be discarded.

    Schema:
    [
      {{
        "ingredient": "UPPERCASE_NAME",
        "shared_compounds": ["Chemical A", "Chemical B", "Chemical C"],
        "flavor_score": <float 0.50-0.99 evaluating chemical profile match>,
        "texture_score": <float 0.10-0.99 evaluating physical performance in the recipe context>,
        "overall_score": <float 0.50-0.99 combining both>
      }}
    ]
    """
    
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash-lite', contents=fallback_prompt)
        fallback_data = clean_ai_json(response.text)
        
        if fallback_data:
            save_ai_substitutes_to_graph(ingredient_name, fallback_data)
            
        formatted_fallback = [
            {
                "ingredient": item["ingredient"],
                "shared_flavor_compounds": len(item.get("shared_compounds", [])),
                "scores": {
                    "flavor": item.get("flavor_score", 0),
                    "texture": item.get("texture_score", 0),
                    "overall": item.get("overall_score", 0)
                },
                "dietary_compliance": restriction if restriction else "Standard",
                "recipe_context": recipe_context if recipe_context else "General"
            } for item in fallback_data
        ]

        return {
            "status": "success",
            "source": "gemini_molecular_rag",
            "target_ingredient": ingredient_name.upper(),
            "substitutes": formatted_fallback
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Molecular Query Failed: {str(e)}")

# --- ENGINE 2: PHILOSOPHICAL GRAPH (SUPABASE / TCM) ---

@router.get("/api/substitute/philosophical/{ingredient_name}")
async def get_philosophical_substitutes(ingredient_name: str):
    """
    Queries Supabase to find ingredients that match the exact 
    Yin-Yang and Five Element profile of the target ingredient,
    ensuring the energetic balance of the dish is maintained.
    """
    try:
        # 1. Fetch the target ingredient's TCM profile
        # Use ilike for case-insensitive matching
        target = supabase.table("ingredients").select("*").ilike("name", ingredient_name).execute()
        
        if not target.data:
            raise HTTPException(status_code=404, detail="Ingredient not found in the ontology database.")
            
        target_data = target.data[0]
        t_element = target_data.get("five_element")
        t_thermal = target_data.get("thermal_property")
        
        if not t_element or not t_thermal:
            return {
                "status": "incomplete",
                "message": f"TCM attributes missing for {ingredient_name}. Please run the Chef AI analysis via the database insertion first."
            }

        # 2. Query Supabase for ingredients with matching Element and Thermal properties
        subs = supabase.table("ingredients").select("name").eq("five_element", t_element).eq("thermal_property", t_thermal).neq("id", target_data["id"]).limit(10).execute()
        
        return {
            "status": "success",
            "source": "supabase_tcm_ontology",
            "target": target_data["name"],
            "philosophy_profile": {
                "element": t_element,
                "thermal_property": t_thermal
            },
            "philosophically_balanced_substitutes": [sub["name"] for sub in subs.data]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Philosophical Query Failed: {str(e)}")