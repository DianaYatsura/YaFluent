import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str

    OPENAI_API_KEY: str
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str

    WEBHOOK_URL: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"), extra="ignore"
    )


settings = Settings()
