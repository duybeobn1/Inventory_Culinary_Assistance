from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from db.neo4j import neo4j_driver, get_neo4j_session
from db.ai import glm_client, clean_ai_json
from db.supabase import supabase
from logging_config import logger

router = APIRouter(tags=["Flavor Matrix & Philosophy"])


def save_ai_substitutes_to_graph(target_ingredient: str, substitutes_list: list):
    query = """
    MERGE (target:Ingredient {name: toUpper($target_name)})

    WITH target
    UNWIND $subs AS sub

    MERGE (sub_node:Ingredient {name: toUpper(sub.ingredient)})

    MERGE (target)-[r:IS_SUBSTITUTE_FOR]->(sub_node)
    SET r.score = COALESCE(sub.overall_score, 0.0),
        r.flavor_score = COALESCE(sub.flavor_score, 0.0),
        r.ai_generated = true

    WITH target, sub_node, sub.shared_compounds AS compounds
    UNWIND compounds AS comp_name

    MERGE (c:Compound {name: toUpper(comp_name)})

    MERGE (target)-[:HAS_COMPOUND {ai_generated: true}]->(c)
    MERGE (sub_node)-[:HAS_COMPOUND {ai_generated: true}]->(c)
    """

    try:
        with get_neo4j_session() as session:
            session.run(
                query, target_name=target_ingredient, subs=substitutes_list
            )
            logger.info(
                f"Molecular graph updated for {target_ingredient} and {len(substitutes_list)} substitutes"
            )
    except Exception as e:
        logger.error(f"Failed to save molecular data to graph: {e}")


@router.get("/api/substitute/molecular/{ingredient_name}")
async def get_molecular_substitutes(
    ingredient_name: str,
    restriction: Optional[str] = Query(
        None, description="e.g., Vegan, Nut-Free, Keto"
    ),
    recipe_context: Optional[str] = Query(
        None, description="e.g., Baking a cake, making a soup, raw salad"
    ),
):
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j database is not connected.")

    chemistry_query = "MATCH (target:Ingredient {name: toUpper($name)})-[:HAS_COMPOUND]->(c:Compound) RETURN collect(c.name) AS compounds"
    known_compounds = []
    try:
        with get_neo4j_session() as session:
            chem_result = session.run(chemistry_query, name=ingredient_name)
            record = chem_result.single()
            if record and record["compounds"]:
                known_compounds = record["compounds"]
    except Exception as e:
        logger.warning(f"Chemistry extraction failed for {ingredient_name}: {e}")

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
            with get_neo4j_session() as session:
                result = session.run(sub_query, name=ingredient_name)
                substitutes = [
                    {
                        "ingredient": rec["substitute"],
                        "shared_flavor_compounds": rec["shared_compounds"],
                        "overall_score": rec["explicit_score"],
                    }
                    for rec in result
                ]

            if substitutes:
                return {
                    "status": "success",
                    "source": "neo4j_graph",
                    "target_ingredient": ingredient_name.upper(),
                    "substitutes": substitutes,
                }
        except Exception as e:
            logger.warning(f"Graph query failed, falling back to AI: {e}")

    logger.info(
        f"Molecular AI lookup for [{ingredient_name}] | Diet: {restriction} | Context: {recipe_context}"
    )

    chem_context = (
        f"Known markers for target: {', '.join(known_compounds)}"
        if known_compounds
        else "No base chemistry known. Perform molecular synthesis."
    )
    diet_context = (
        f"DIET CONSTRAINT: Must be {restriction}."
        if restriction
        else "No dietary restrictions."
    )
    usage_context = (
        f"FUNCTIONAL CONTEXT: Functioning for '{recipe_context}'."
        if recipe_context
        else "General culinary utility."
    )

    fallback_prompt = f"""
    Role: Senior Molecular Gastronomist & Flavor Chemist API.
    Task: Provide exactly 5 ingredient substitutes for '{ingredient_name}' and map their defining chemical signatures.

    Context:
    - {chem_context}
    - {diet_context}
    - {usage_context}

    Strict Constraints:
    1. ARRAY ENFORCEMENT: You MUST return a JSON ARRAY [ ], even if there is only one result.
    2. ONLY JSON: Return ONLY a raw, minified JSON array. Do NOT include any conversational text or markdown.
    3. MOLECULAR MAPPING: The 'shared_compounds' array MUST contain the scientific names of 3-5 primary chemical flavor markers.
    4. COMPLIANCE: If a substitute violates the diet constraint ({restriction}), it must be discarded.

    Schema:
    [
      {{
        "ingredient": "UPPERCASE_NAME",
        "shared_compounds": ["Chemical A", "Chemical B", "Chemical C"],
        "flavor_score": <float 0.50-0.99>,
        "texture_score": <float 0.10-0.99>,
        "overall_score": <float 0.50-0.99>
      }}
    ]
    """

    try:
        glm_resp = glm_client.chat.completions.create(
            model="glm-4.7-flash", messages=[{"role": "user", "content": fallback_prompt}]
        )
        fallback_data = clean_ai_json(glm_resp.choices[0].message.content)

        if fallback_data:
            save_ai_substitutes_to_graph(ingredient_name, fallback_data)

        formatted_fallback = [
            {
                "ingredient": item["ingredient"],
                "shared_flavor_compounds": len(item.get("shared_compounds", [])),
                "scores": {
                    "flavor": item.get("flavor_score", 0),
                    "texture": item.get("texture_score", 0),
                    "overall": item.get("overall_score", 0),
                },
                "dietary_compliance": restriction if restriction else "Standard",
                "recipe_context": recipe_context if recipe_context else "General",
            }
            for item in fallback_data
        ]

        return {
            "status": "success",
            "source": "glm_molecular_rag",
            "target_ingredient": ingredient_name.upper(),
            "substitutes": formatted_fallback,
        }

    except Exception as e:
        logger.exception("Molecular query failed")
        raise HTTPException(status_code=500, detail=f"Molecular query failed: {e}")


@router.get("/api/substitute/philosophical/{ingredient_name}")
async def get_philosophical_substitutes(ingredient_name: str):
    try:
        target = (
            supabase.table("ingredients")
            .select("*")
            .ilike("name", ingredient_name)
            .execute()
        )

        if not target.data:
            raise HTTPException(
                status_code=404, detail="Ingredient not found in the ontology database."
            )

        target_data = target.data[0]
        t_element = target_data.get("five_element")
        t_thermal = target_data.get("thermal_property")

        if not t_element or not t_thermal:
            return {
                "status": "incomplete",
                "message": f"TCM attributes missing for {ingredient_name}. Run Chef AI analysis first.",
            }

        subs = (
            supabase.table("ingredients")
            .select("name")
            .eq("five_element", t_element)
            .eq("thermal_property", t_thermal)
            .neq("id", target_data["id"])
            .limit(10)
            .execute()
        )

        return {
            "status": "success",
            "source": "supabase_tcm_ontology",
            "target": target_data["name"],
            "philosophy_profile": {
                "element": t_element,
                "thermal_property": t_thermal,
            },
            "philosophically_balanced_substitutes": [
                sub["name"] for sub in subs.data
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Philosophical query failed")
        raise HTTPException(
            status_code=500, detail=f"Philosophical query failed: {e}"
        )
