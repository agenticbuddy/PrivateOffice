"""Application settings, loaded from environment.

Single source of truth for service URLs, secrets and storage config. Everything
is overridable via env so the same code runs in compose, tests and CI.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Core
    secret_key: str = "dev-secret-change-me"
    session_cookie: str = "ws_session"
    public_origin: str = "http://localhost"
    static_dir: str = "/app/static"

    # Database (async SQLAlchemy URL). Tests override with sqlite+aiosqlite.
    database_url: str = "postgresql+asyncpg://workspace:workspace@postgres:5432/workspace"

    # MinIO / S3
    minio_endpoint: str = "http://minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin123"
    minio_bucket: str = "documents"

    # Editor
    editor_internal_url: str = "http://editor:9980"
    wopi_host_url: str = "http://app:8000"

    # Bootstrap admin (created on first boot if absent)
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_name: str = "Administrator"

    # Session / token lifetimes (seconds)
    session_ttl: int = 60 * 60 * 24 * 14
    magic_link_ttl: int = 60 * 60 * 24 * 7
    wopi_token_ttl: int = 60 * 60 * 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
