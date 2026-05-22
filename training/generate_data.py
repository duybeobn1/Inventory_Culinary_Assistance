import json
import time
import os
import sys
import signal

import ollama

BOOKS_PATH = "raw_master_theory.txt"
INGREDIENTS_PATH = "ingredients_2000.txt"
OUTPUT_PATH = "tcm_culinary_dataset.jsonl"
CHECKPOINT_PATH = "generate_data_checkpoint.json"
MODEL = "qwen3:14b"
BATCH_SIZE = 5

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

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {"processed_idx": 0, "chunk_idx": 0}

def save_checkpoint(processed_idx, chunk_idx):
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({"processed_idx": processed_idx, "chunk_idx": chunk_idx}, f)

def append_examples(examples):
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

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
        print(f"  Error: {e}", flush=True)
        return []

def main():
    if not os.path.exists(BOOKS_PATH):
        print(f"Missing {BOOKS_PATH}. Run extract_books.py first.")
        sys.exit(1)

    book_text = load_text(BOOKS_PATH)
    ingredients = [l.strip() for l in load_text(INGREDIENTS_PATH).split("\n") if l.strip()]
    chunks = chunk_book(book_text)

    checkpoint = load_checkpoint()
    start_idx = checkpoint["processed_idx"]
    chunk_idx = checkpoint["chunk_idx"]
    seen = set()

    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH) as f:
            for line in f:
                try:
                    ex = json.loads(line)
                    seen.add((ex.get("instruction", ""), ex.get("output", "")))
                except json.JSONDecodeError:
                    pass

    print(f"Loaded {len(chunks)} chunks, {len(ingredients)} ingredients")
    print(f"Resuming from ingredient index {start_idx} (chunk {chunk_idx})")
    print(f"Already have {len(seen)} unique examples in {OUTPUT_PATH}")
    print("Press Ctrl+C to save checkpoint and exit cleanly", flush=True)

    running = True
    def handle_signal(sig, frame):
        nonlocal running
        print(f"\nReceived signal, saving checkpoint (idx={start_idx})...", flush=True)
        save_checkpoint(start_idx, chunk_idx)
        print("Checkpoint saved. Exiting.", flush=True)
        running = False
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    i = start_idx
    while i < len(ingredients) and running:
        batch = ingredients[i:i + BATCH_SIZE]
        chunk = chunks[chunk_idx % len(chunks)]
        chunk_idx += 1

        examples = generate_examples(chunk, batch)
        if examples:
            new = []
            for ex in examples:
                key = (ex.get("instruction", ""), ex.get("output", ""))
                if key not in seen and ex.get("instruction") and ex.get("output"):
                    seen.add(key)
                    new.append(ex)
            if new:
                append_examples(new)
                print(f"  +{len(new)} examples  |  batch {i//BATCH_SIZE + 1}/{len(ingredients)//BATCH_SIZE + 1}  |  total {len(seen)}", flush=True)

        i += BATCH_SIZE
        save_checkpoint(i, chunk_idx)
        time.sleep(1)

    if running:
        print(f"\nDone! {len(seen)} examples → {OUTPUT_PATH}", flush=True)
        os.remove(CHECKPOINT_PATH)
    else:
        print(f"Interrupted at ingredient index {i}", flush=True)

if __name__ == "__main__":
    main()
