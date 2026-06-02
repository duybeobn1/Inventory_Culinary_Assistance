import re
import json
import base64
from zai import ZaiClient, ZhipuAiClient
from config import get_settings
from logging_config import logger

settings = get_settings()

# Use ZaiClient for overseas endpoint (api.z.ai)
glm_client = ZaiClient(api_key=settings.zai_api_key)


def clean_ai_json(raw_text: str) -> dict | list:
    start_index = -1
    for i, char in enumerate(raw_text):
        if char in ("[", "{"):
            start_index = i
            break

    if start_index == -1:
        raise ValueError("No JSON detected in AI response.")

    try:
        content = raw_text[start_index:]
        decoder = json.JSONDecoder()
        obj, end_pos = decoder.raw_decode(content)
        return obj
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


async def call_chef_ai(ingredient_name: str, timeout: float = 120.0) -> str:
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.chef_ai_url,
            json={"ingredient": ingredient_name},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("analysis", "")


async def call_ollama(prompt: str, model: str = "qwen3:14b", timeout: float = 180.0) -> str:
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.ollama_url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.4},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
