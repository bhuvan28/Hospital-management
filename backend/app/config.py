from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RMH HCTM UKM Operations Platform"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    secret_key: str = Field(default="INSECURE_DEV_ONLY_CHANGE_ME")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cookie_name: str = "rmh_session"
    csrf_cookie_name: str = "rmh_csrf"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rmh_hctm"
    postgres_user: str = "rmh"
    postgres_password: str = "rmh_dev_only"
    database_url: str | None = None

    seed_on_startup: bool = False
    seed_admin_email: str = "admin@rmh.example.com"
    seed_admin_password: str = "DevAdmin!2026"

    @field_validator("secret_key")
    @classmethod
    def reject_placeholder_in_production(cls, value: str, info):
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
