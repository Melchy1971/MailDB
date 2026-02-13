from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://mail:mail@localhost:5432/mailknowledge"
    REDIS_URL: str = "redis://localhost:6379/0"
    UPLOADS_DIR: str = "/uploads"


settings = Settings()
