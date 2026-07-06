"""
Application settings loaded from environment variables.

Never hardcode secrets — everything comes from env vars or .env file.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database — default to SQLite for zero-config local dev.
    # On Render, set DATABASE_URL to the PostgreSQL connection string.
    DATABASE_URL: str = "sqlite:///./ielts.db"

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Poe API (OpenAI-compatible)
    POE_API_KEY: str = ""
    POE_MODEL: str = "gpt-5.4-nano"

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:5173"

    # Email — Gmail SMTP (free: 500 emails/day)
    GMAIL_APP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
