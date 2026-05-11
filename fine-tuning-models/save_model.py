import os
from huggingface_hub import login

# 1. Save the model locally as a backup
local_save_path = "lora_model_cordonbleu"
model.save_pretrained(local_save_path)
tokenizer.save_pretrained(local_save_path)
print(f"Model saved locally to {local_save_path}/")

# 2. Authenticate with Hugging Face
# In Google Colab, it is best to store your token in the 'Secrets' tab (the key icon on the left)
# If you haven't set it in secrets, you can temporarily paste it below as a string
try:
    from google.colab import userdata
    hf_token = userdata.get('HF_TOKEN')
except Exception:
    hf_token = input("Please enter your Hugging Face Write Token: ")

login(token=hf_token)

# 3. Push to Hugging Face Hub
# Replace this with your actual HF username and desired model name
hf_repo_id = "duybeobn1/ICA"

print(f"Pushing LoRA adapters to {hf_repo_id}...")

# This will upload the adapter_config.json and adapter_model.safetensors
model.push_to_hub(hf_repo_id)
tokenizer.push_to_hub(hf_repo_id)

print("Export complete. Your model is now live on Hugging Face!")