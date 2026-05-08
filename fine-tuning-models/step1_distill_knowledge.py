import os
import time
import json
from zai import ZaiClient
from dotenv import load_dotenv

load_dotenv()
client = ZaiClient(api_key=os.environ.get("ZAI_API_KEY"))

input_file = "raw_master_theory.txt"
output_file = "core_philosophy.txt"

def run_distillation():
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Split text into manageable chunks (approx 50k characters each)
    chunk_size = 50000
    chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
    print(f"Loaded {len(raw_text)} characters. Split into {len(chunks)} chunks.")

    extracted_notes = []

    # Phase 1: Mapping (Filter relevant culinary data)
    map_prompt = (
        "You are a research assistant. Read the following text from ancient medical canons. "
        "Extract every rule related to: "
        "1. Five Elements and Flavors (Sour, Bitter, Sweet, Pungent, Salty). "
        "2. Yin-Yang properties in food (Thermal properties, growth patterns). "
        "If the section only discusses acupuncture or medical dosages, respond only with: NO RELEVANT DATA. "
        "Otherwise, summarize the culinary rules in concise English."
    )

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        try:
            response = client.chat.completions.create(
                model="glm-4.7-flash",
                messages=[
                    {"role": "system", "content": map_prompt},
                    {"role": "user", "content": f"Text fragment:\n\n{chunk}"}
                ],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            
            if "NO RELEVANT DATA" not in result.upper():
                extracted_notes.append(result)
            
            time.sleep(0.5) 
        except Exception as e:
            print(f"Error at chunk {i+1}: {e}")

    if not extracted_notes:
        print("No culinary data found in the provided text.")
        return

    # Phase 2: Reduction (Synthesize into final Knowledge Base)
    print(f"Extracted relevant data from {len(extracted_notes)}/{len(chunks)} chunks.")
    print("Synthesizing final Knowledge Base...")

    combined_notes = "\n\n--- NEXT SECTION ---\n\n".join(extracted_notes)

    reduce_prompt = (
        "You are an expert in Traditional Chinese Medicine, Macrobiotics, and Le Cordon Bleu techniques. "
        "Synthesize the provided notes into a structured Knowledge Base in English. "
        "Structure the output into three specific sections: "
        "1. The Five Elements (Nguy Hanh) and Flavor Mappings. "
        "2. The Yin-Yang Properties (Ohsawa guidelines). "
        "3. Ingredient Categorization Logic (How to determine properties of a new ingredient). "
        "Output only the structured rules."
    )

    try:
        response = client.chat.completions.create(
            model="glm-4.7-flash",
            messages=[
                {"role": "system", "content": reduce_prompt},
                {"role": "user", "content": f"Extracted Notes:\n\n{combined_notes}"}
            ],
            temperature=0.2
        )
        final_knowledge = response.choices[0].message.content
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_knowledge)
            
        print(f"Synthesis complete. Knowledge Base saved to: {output_file}")
    except Exception as e:
        print(f"Synthesis error: {e}")

if __name__ == "__main__":
    run_distillation()