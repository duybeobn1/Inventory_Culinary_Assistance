import json
import subprocess
import sys
import os
import random
from pathlib import Path

# Load HF token from backend/.env
env_path = Path(__file__).parent.parent / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("HUGGING_FACE_TOKEN="):
            os.environ["HF_TOKEN"] = line.split("=", 1)[1].strip()
            break

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ITERS = 500
BATCH_SIZE = 4
GRAD_ACC = 2
LR = 1e-4
NUM_LAYERS = 16
MAX_SEQ = 2048
SAVE_EVERY = 100
DATA_DIR = "mlx_data"
ADAPTER_DIR = "mlx_adapter"
MERGED_DIR = "mlx_model_merged"

DATASETS = [
    "tcm_culinary_dataset.jsonl",
    "existing_dataset/massive_culinary_dataset_clean.jsonl",
]

def load_all(dataset_paths):
    all_examples = []
    for path in dataset_paths:
        if not os.path.exists(path):
            print(f"  Skipping (not found): {path}")
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    if ex.get("instruction") and ex.get("output"):
                        all_examples.append(ex)
                except json.JSONDecodeError:
                    pass
    return all_examples

def to_mlx_chat(examples):
    results = []
    for ex in examples:
        results.append({
            "messages": [
                {"role": "user", "content": ex["instruction"]},
                {"role": "assistant", "content": ex["output"]},
            ]
        })
    return results

def convert_data():
    print("Loading datasets...")
    examples = load_all(DATASETS)
    print(f"Total examples: {len(examples)}")

    random.shuffle(examples)
    n = len(examples)
    train_end = int(n * 0.9)
    valid_end = int(n * 0.95)

    train_raw = examples[:train_end]
    valid_raw = examples[train_end:valid_end]
    test_raw = examples[valid_end:]

    splits = {
        "train": to_mlx_chat(train_raw),
        "valid": to_mlx_chat(valid_raw),
        "test": to_mlx_chat(test_raw),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    for name, data in splits.items():
        path = os.path.join(DATA_DIR, f"{name}.jsonl")
        with open(path, "w") as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"  {name}: {len(data)} examples → {path}")

def train():
    cmd = [
        sys.executable, "-m", "mlx_lm", "lora",
        "--model", BASE_MODEL,
        "--train",
        "--data", DATA_DIR,
        "--num-layers", str(NUM_LAYERS),
        "--batch-size", str(BATCH_SIZE),
        "--grad-accumulation-steps", str(GRAD_ACC),
        "--learning-rate", str(LR),
        "--iters", str(ITERS),
        "--max-seq-length", str(MAX_SEQ),
        "--adapter-path", ADAPTER_DIR,
        "--save-every", str(SAVE_EVERY),
        "--steps-per-report", "10",
        "--steps-per-eval", "50",
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)
    print(f"\nAdapter saved to {ADAPTER_DIR}/")

def merge():
    cmd = [
        sys.executable, "-m", "mlx_lm", "fuse",
        "--model", BASE_MODEL,
        "--adapter-path", ADAPTER_DIR,
        "--save-path", MERGED_DIR,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)
    print(f"\nMerged model saved to {MERGED_DIR}/")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["convert", "train", "merge", "all"])
    args = parser.parse_args()

    if args.step in ("convert", "all"):
        convert_data()
    if args.step in ("train", "all"):
        train()
    if args.step in ("merge", "all"):
        merge()
