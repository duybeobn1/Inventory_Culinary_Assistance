import json
import os

input_file = "massive_culinary_dataset_clean.jsonl"
final_output_file = "massive_culinary_dataset_strict.jsonl"

valid_lines = []
removed_count = 0

print("Starting strict type validation...")

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
else:
    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # STRICT CHECK: Both keys must exist AND both must be strings
                if (
                    "instruction" in data and 
                    "output" in data and 
                    isinstance(data["instruction"], str) and 
                    isinstance(data["output"], str)
                ):
                    # We create a fresh, perfectly clean dictionary to strip any hidden garbage
                    clean_data = {
                        "instruction": data["instruction"],
                        "output": data["output"]
                    }
                    valid_lines.append(json.dumps(clean_data, ensure_ascii=False))
                else:
                    print(f"Dropped line {line_num}: 'output' or 'instruction' was not a string.")
                    removed_count += 1
                    
            except Exception as e:
                print(f"Dropped line {line_num} due to parse error: {e}")
                removed_count += 1

    # Save the strictly validated lines
    with open(final_output_file, "w", encoding="utf-8") as f:
        for line in valid_lines:
            f.write(line + "\n")

    print("\n--- Final Cleanup Results ---")
    print(f"Removed {removed_count} badly typed entries.")
    print(f"Strictly clean dataset saved to '{final_output_file}' with {len(valid_lines)} perfect entries.")