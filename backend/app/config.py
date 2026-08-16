"""应用配置"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./scheduler.db"
    DEBUG: bool = False

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # LLM API
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
