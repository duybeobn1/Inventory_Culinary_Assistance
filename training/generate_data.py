import json
import time
import random
import ollama

BOOKS_PATH = "raw_master_theory.txt"
PHILOSOPHY_PATH = "core_philosophy.txt"
INGREDIENTS_PATH = "ingredients_2000.txt"
OUTPUT_PATH = "tcm_culinary_dataset.jsonl"
MODEL = "qwen3:14b"

SYSTEM_PROMPT = """You are a Master Chef specialized in Vietnamese Five Elements (Ngũ Hành) and Yin-Yang (Âm Dương) gastronomy, trained at Le Cordon Bleu.

You will analyze culinary texts and generate training data for an AI chef model.

Output ONLY a raw valid JSON array of objects. No markdown, no code fences.
Each object must have exactly:
- "instruction": user query about TCM culinary knowledge
- "output": expert response using knowledge from the provided text
- "type": one of ["tcm_profile", "substitute", "pairing", "seasonal", "health"]

Generate 2-3 examples per request, varying the types."""

def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_book(text, max_chars=4000):
    lines = text.split("\n")
    chunks, current, current_len = [], [], 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if current_len + len(stripped) > max_chars:
            chunks.append("\n".join(current))
            current, current_len = [stripped], len(stripped)
        else:
            current.append(stripped)
            current_len += len(stripped)
    if current:
        chunks.append("\n".join(current))
    return chunks

def get_batches(items, size=5):
    random.shuffle(items)
    for i in range(0, len(items), size):
        yield items[i:i + size]

def generate_examples(chunk, ingredients_batch):
    ingredients_str = ", ".join(ingredients_batch)
    user_prompt = f"""Using the culinary text below as reference, generate training examples for: {ingredients_str}

Reference:
{chunk[:3000]}

Create diverse examples with TCM terminology from the reference."""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.7, "num_predict": 2048},
        )
        raw = response["message"]["content"]
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"  Error: {e}")
        return []

def main():
    book_text = load_text(BOOKS_PATH)
    ingredients = [l.strip() for l in load_text(INGREDIENTS_PATH).split("\n") if l.strip()]
    chunks = chunk_book(book_text)
    print(f"Loaded {len(chunks)} chunks, {len(ingredients)} ingredients")

    all_examples, seen, chunk_idx = [], set(), 0
    target = min(len(ingredients) * 3, 3000)

    for batch in get_batches(ingredients):
        print(f"\nBatch starting with: {batch[0]}...")
        chunk = chunks[chunk_idx % len(chunks)]
        chunk_idx += 1

        examples = generate_examples(chunk, batch)
        if not examples:
            time.sleep(2)
            continue

        for ex in examples:
            key = (ex.get("instruction", ""), ex.get("output", ""))
            if key not in seen and ex.get("instruction") and ex.get("output"):
                seen.add(key)
                all_examples.append(ex)

        print(f"  Total: {len(all_examples)} examples")
        if len(all_examples) >= target:
            break
        time.sleep(1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nDone! {len(all_examples)} examples → {OUTPUT_PATH}")
    counts = {}
    for ex in all_examples:
        counts[ex.get("type", "?")] = counts.get(ex.get("type", "?"), 0) + 1
    print(f"Types: {json.dumps(counts, indent=2)}")

if __name__ == "__main__":
    main()
