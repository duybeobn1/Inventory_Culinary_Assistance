import json
import subprocess
import sys

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
LORA_RANK = 16
LORA_ALPHA = 32
LR = 1e-4
EPOCHS = 3
BATCH_SIZE = 4
GRAD_ACC = 2
MAX_SEQ = 2048
OUTPUT_DIR = "mlx_model"
TRAIN_FILE = "tcm_culinary_dataset.jsonl"

def convert_to_mlx_format(input_path, output_path):
    """Convert our JSONL to MLX chat format."""
    with open(input_path, "r") as f:
        examples = [json.loads(line) for line in f if line.strip()]

    with open(output_path, "w") as out:
        for ex in examples:
            entry = {
                "messages": [
                    {"role": "user", "content": ex["instruction"]},
                    {"role": "assistant", "content": ex["output"]},
                ]
            }
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Converted {len(examples)} examples → {output_path}")

def train():
    mlx_train = "mlx_lm.lora" if not subprocess.run(["which", "mlx_lm.lora"]).returncode else "mlx_lm.lora"
    subprocess.run([
        sys.executable, "-m", mlx_train,
        "--model", BASE_MODEL,
        "--train", "--data", "mlx_data.jsonl",
        "--lora-layers", str(LORA_RANK),
        "--batch-size", str(BATCH_SIZE),
        "--grad-accum-steps", str(GRAD_ACC),
        "--lr", str(LR),
        "--num-epochs", str(EPOCHS),
        "--max-seq-length", str(MAX_SEQ),
        "--adapter-path", OUTPUT_DIR,
        "--save-every", "100",
    ])
    print(f"Training complete. Adapter saved to {OUTPUT_DIR}/")

def merge():
    subprocess.run([
        sys.executable, "-m", "mlx_lm.fuse",
        "--model", BASE_MODEL,
        "--adapter-path", OUTPUT_DIR,
        "--save-path", f"{OUTPUT_DIR}_merged",
    ])
    print(f"Merged model saved to {OUTPUT_DIR}_merged/")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["convert", "train", "merge", "all"])
    args = parser.parse_args()

    if args.step in ("convert", "all"):
        convert_to_mlx_format(TRAIN_FILE, "mlx_data.jsonl")
    if args.step in ("train", "all"):
        train()
    if args.step in ("merge", "all"):
        merge()
