from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agent-yhzh"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8123

    database_url: str = (
        "postgresql+asyncpg://agent_yhzh:agent_yhzh_dev@127.0.0.1:5432/agent_yhzh"
    )
    checkpoint_database_url: str = (
        "postgresql://agent_yhzh:agent_yhzh_dev@127.0.0.1:5432/agent_yhzh"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"

    admin_api_key: str = "change-me-admin-key"
    user_hash_salt: str = "change-me-user-salt"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    model_name: str = "openai/gpt-5.4-mini"
    openai_api_key: str = ""

    candidate_review_threshold: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
