import os
import json
import time
from zai import ZaiClient
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# 1. Initialize the ZaiClient exactly to your specs
client = ZaiClient(api_key=os.environ.get("ZHIPU_API_KEY"))

# 2. Seed Ingredients
ingredients = [
    "Beef", "Duck", "Pork Belly", "Tofu", "Seaweed", 
    "Potato", "Carrot", "Lime", "Chili", "Ginger", 
    "Star Anise", "Butter", "Olive Oil", "Cream"
]

training_data = []

def generate_philosophical_example(target, retries=3):
    system_prompt = """
    You are a Master Chef model. You were trained at Le Cordon Bleu and study at Universite Lyon 1. You are an expert in Vietnamese Five Elements (Nguy Hanh) and Yin-Yang (Am Duong) gastronomy.
    
    A user will ask for a substitute for a specific ingredient. You must reply by identifying the thermal property and element of the target, suggesting a substitute, and explaining how to balance the thermal gap.
    
    CRITICAL CONSTRAINTS:
    1. Keep your explanation concise and impactful (3 to 4 sentences maximum).
    2. Output ONLY a raw, valid JSON object. Do NOT use markdown blocks like ```json.
    
    Schema:
    {
      "instruction": "Suggest a philosophically balanced substitute for [Ingredient].",
      "output": "[Your concise, expert explanation]"
    }
    """
    
    for attempt in range(retries):
        try:
            # Using the ZaiClient completions method
            response = client.chat.completions.create(
                model="glm-4.7-flash", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate the JSON training example for: {target}"}
                ]
            )
            
            # Extract content using the structure from your snippet
            raw_text = response.choices[0].message.content
            
            if not raw_text:
                print(f"  [Attempt {attempt+1}] Empty response. Retrying...")
                time.sleep(1)
                continue
                
            # Clean text just in case GLM adds markdown
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            return json.loads(clean_text)
            
        except json.JSONDecodeError:
            print(f"  [Attempt {attempt+1}] JSON formatting failed. Retrying...")
            time.sleep(1)
            continue
        except Exception as e:
            print(f"  [Attempt {attempt+1}] API Error: {e}")
            time.sleep(2)
            continue
            
    print(f"Completely failed to generate for {target} after {retries} attempts.")
    return None

# --- EXECUTION LOOP ---
print("Firing up ZaiClient (GLM-4.7-Flash): Synthesizing Culinary Philosophy Dataset...")

for item in ingredients:
    print(f"Cooking up data for: {item}...")
    example = generate_philosophical_example(item)
    
    if example:
        training_data.append(example)
        print(f"Success: {item}")
    else:
        print(f"Skipped {item} due to error.")
        
    # Brief pause to respect rate limits
    time.sleep(0.5) 

# Save to JSONL
output_file = "culinary_philosophy_dataset.jsonl"
if training_data:
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in training_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\nDataset generated successfully! Saved to {output_file}")
    print(f"Total examples: {len(training_data)}")
else:
    print("\nNo data was generated.")