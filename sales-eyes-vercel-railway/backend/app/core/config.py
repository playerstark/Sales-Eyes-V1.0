import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Sales Eyes API"
    ENV: str = "development"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://salesstalker:salesstalker_dev_pw@database:5432/sales_stalker"

    # Auth
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # External APIs
    # DeepSeek V4 Flash Configuration
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_ENDPOINT: str = "https://aicredits.in/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-chat"  # V4 Flash
    
    # NewsAPI Configuration
    NEWSAPI_KEY: str | None = None
    NEWSAPI_ENDPOINT: str = "https://newsapi.org/v2"

    # LinkedIn Scraper API Configuration
    LINKEDIN_API_KEY: str | None = None
    LINKEDIN_API_HOST: str = "linkedin-data-api.p.rapidapi.com"
    LINKEDIN_API_ENDPOINT: str = "https://linkedin-data-api.p.rapidapi.com"


settings = Settings()
