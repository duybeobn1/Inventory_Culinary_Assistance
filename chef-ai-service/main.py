from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

app = FastAPI(title="Chef AI Inference Service", version="2.0")

MODEL_PATH = "../training/mlx_model_merged"
device = "mps" if torch.backends.mps.is_available() else "cpu"

print(f"Loading model from {MODEL_PATH} onto {device.upper()}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float16).to(device)
model.eval()
print(f"Model ready on {device.upper()}!")


class InferenceRequest(BaseModel):
    ingredient: str


SYSTEM_PROMPT = "You are a Master Chef specialized in Vietnamese Five Elements (Ngũ Hành) and Yin-Yang (Âm Dương) gastronomy."


@app.post("/generate")
async def generate_culinary_logic(request: InferenceRequest):
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Suggest a philosophically balanced substitute for {request.ingredient}."},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                pad_token_id=tokenizer.eos_token_id,
            )

        result = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return {"analysis": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
