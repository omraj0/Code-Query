from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    DATABASE_URL: str
    GEMINI_API_KEY: str
    JWT_SECRET_KEY: str = "supersecretkeyshouldbechanged"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Optional: Log level
    LOG_LEVEL: str = "INFO"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
