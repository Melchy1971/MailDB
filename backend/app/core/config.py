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
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    EMBEDDING_DIM: int = 768
    # Comma-separated or JSON array — e.g. '["http://localhost:3000"]'
    # Use ["*"] for local dev; restrict in production.
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]


settings = Settings()
