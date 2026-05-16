import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""
    gemini_api_key: str = ""
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
    chef_ai_url: str = "http://127.0.0.1:8001/generate"
    ollama_url: str = "http://127.0.0.1:11434/api/chat"
    kafka_bootstrap_servers: str = "localhost:9092"
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    expiry_check_days: int = 3
    auth_enabled: bool = True
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
