# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM
# from peft import PeftModel

# app = FastAPI(title="Chef AI Inference Service", version="1.0")

# # --- CẤU HÌNH MODEL ---
# LORA_ADAPTER = "duybeobn1/ICA"
# BASE_MODEL = "unsloth/llama-3-8b-Instruct-bnb-4bit"

# print("Loading LLM into VRAM")
# tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
# base_model = AutoModelForCausalLM.from_pretrained(
#     BASE_MODEL, load_in_4bit=True, device_map="auto"
# )
# model = PeftModel.from_pretrained(base_model, LORA_ADAPTER)
# model.eval()
# print("LLM Ready for Inference!")

# class InferenceRequest(BaseModel):
#     ingredient: str

# ALpaca_TEMPLATE = """Below is an instruction that describes a culinary task. Write a response that appropriately completes the request.

# ### Instruction:
# Suggest a philosophically balanced substitute for {}.

# ### Response:
# """

# @app.post("/generate")
# async def generate_culinary_logic(request: InferenceRequest):
#     try:
#         prompt = ALpaca_TEMPLATE.format(request.ingredient)
#         inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        
#         with torch.no_grad():
#             outputs = model.generate(**inputs, max_new_tokens=256, pad_token_id=tokenizer.eos_token_id)
            
#         result = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
#         return {"analysis": result.strip()}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # Khởi chạy: uvicorn main:app --host 0.0.0.0 --port 8001



from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os

app = FastAPI(title="Chef AI Inference Service", version="1.0")

# --- CẤU HÌNH MODEL ---
LORA_ADAPTER = "duybeobn1/ICA" # Thay tên của bạn vào đây
# Dùng bản base không nén (non-4bit) vì Mac không hỗ trợ bitsandbytes tốt
BASE_MODEL = "unsloth/llama-3-8b-Instruct" 

# Kiểm tra xem máy Mac có hỗ trợ Metal (MPS) không
device = "mps" if torch.backends.mps.is_available() else "cpu"

print(f"Loading LLM into {device.upper()}...")

# Khởi tạo model
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

# Load base model dưới dạng 16-bit để chạy trên Mac
# Remove device_map=device
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    low_cpu_mem_usage=True
).to(device) # Move to MPS after loading
# Đắp LoRA Adapter vào
model = PeftModel.from_pretrained(base_model, LORA_ADAPTER)
model.eval()
print(f"LLM Ready for Inference on {device.upper()}!")

class InferenceRequest(BaseModel):
    ingredient: str

ALpaca_TEMPLATE = """Below is an instruction that describes a culinary task. Write a response that appropriately completes the request.

### Instruction:
Suggest a philosophically balanced substitute for {}.

### Response:
"""

@app.post("/generate")
async def generate_culinary_logic(request: InferenceRequest):
    try:
        prompt = ALpaca_TEMPLATE.format(request.ingredient)
        # Chuyển input vào GPU của Mac (MPS)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs, 
                max_new_tokens=256, 
                pad_token_id=tokenizer.eos_token_id
            )
            
        result = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return {"analysis": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))