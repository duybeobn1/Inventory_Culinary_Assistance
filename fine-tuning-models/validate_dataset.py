import json
import os

input_file = "massive_culinary_dataset.jsonl"
output_file = "massive_culinary_dataset_clean.jsonl"

valid_lines = []
removed_count = 0

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
else:
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                # Keep only lines that strictly match our required schema
                if "instruction" in data and "output" in data:
                    valid_lines.append(line)
                else:
                    removed_count += 1
            except json.JSONDecodeError:
                removed_count += 1

    # Save the strictly validated lines to a new file
    with open(output_file, "w", encoding="utf-8") as f:
        for line in valid_lines:
            f.write(line + "\n")

    print(f"Cleanup complete.")
    print(f"Removed {removed_count} malformed entries.")
    print(f"Clean dataset saved to '{output_file}' with {len(valid_lines)} perfect entries.")