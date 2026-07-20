from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    auto_migrate: bool = True

    admin_api_key: str = "change-me-admin-key"
    admin_service_token: str = "change-me-admin-service-token"
    agent_service_token: str = "change-me-agent-service-token"
    ops_api_key: str = "change-me-ops-key"
    user_hash_salt: str = "change-me-user-salt"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    expose_public_docs: bool = False

    default_tenant_id: str = "default"
    default_space_id: str = "default"
    interaction_retention_days: int = 30
    candidate_review_threshold: int = 2
    candidate_min_distinct_users: int = 2
    request_rate_limit_per_minute: int = 60

    model_name: str = "openai/gpt-5.4-mini"
    openai_api_key: str = ""
    embedding_model: str = "local/hash-1536"
    embedding_dimensions: int = 1536

    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True

    object_store_backend: str = "local"
    object_store_path: str = ".data/objects"
    s3_endpoint_url: str = "http://127.0.0.1:9000"
    s3_access_key: str = "agent_yhzh"
    s3_secret_key: str = "agent_yhzh_dev"
    s3_bucket: str = "agent-yhzh"
    s3_region: str = "us-east-1"
    document_max_bytes: int = 20 * 1024 * 1024
    document_chunk_chars: int = 1200
    document_chunk_overlap: int = 160

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://127.0.0.1:3001"
    otel_exporter_otlp_endpoint: str = ""
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "admin_api_key",
        "admin_service_token",
        "agent_service_token",
        "ops_api_key",
        "user_hash_salt",
    )
    @classmethod
    def reject_default_production_secrets(cls, value: str, info):
        # Environment is validated after the model is built; production startup
        # performs the definitive check in validate_runtime_security().
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def object_store_directory(self) -> Path:
        path = Path(self.object_store_path)
        return path if path.is_absolute() else self.project_root / path

    def validate_runtime_security(self) -> None:
        if self.environment != "production":
            return
        insecure = {
            "admin_api_key": self.admin_api_key,
            "admin_service_token": self.admin_service_token,
            "agent_service_token": self.agent_service_token,
            "ops_api_key": self.ops_api_key,
            "user_hash_salt": self.user_hash_salt,
        }
        bad = [name for name, value in insecure.items() if not value or value.startswith("change-me")]
        if bad:
            raise RuntimeError(
                "Production secrets must be configured: " + ", ".join(sorted(bad))
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
