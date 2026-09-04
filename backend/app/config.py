import socket
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse, urlunparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Docker Compose service names. They resolve only on the compose network.
# Host-side processes (local uvicorn, Alembic, Cloud Agents) must use localhost.
COMPOSE_ONLY_DB_HOSTS = frozenset({"postgres", "db"})


def hostname_resolves(host: str) -> bool:
    """Return True when DNS can resolve host. Used to detect compose-only names."""
    try:
        socket.getaddrinfo(host, None)
        return True
    except OSError:
        return False


def rewrite_unresolvable_compose_url(url: str) -> str:
    """Rewrite compose hostnames in a SQLAlchemy URL to localhost when they do not resolve."""
    parsed = urlparse(url)
    netloc = parsed.netloc
    if not netloc:
        return url
    if "@" in netloc:
        userinfo, hostport = netloc.rsplit("@", 1)
        prefix = f"{userinfo}@"
    else:
        hostport = netloc
        prefix = ""
    host, sep, port = hostport.partition(":")
    if host not in COMPOSE_ONLY_DB_HOSTS or hostname_resolves(host):
        return url
    return urlunparse(parsed._replace(netloc=f"{prefix}localhost{sep}{port}"))


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

    @model_validator(mode="after")
    def fallback_unresolvable_compose_hosts(self):
        """Use localhost when POSTGRES_HOST/DATABASE_URL point at compose DNS that is not resolvable.

        Copying .env.example used to set POSTGRES_HOST=postgres. That name only exists on the
        Docker Compose network, so host-side SQLAlchemy/psycopg failed with
        [Errno -2] Name or service not known.
        """
        if self.postgres_host in COMPOSE_ONLY_DB_HOSTS and not hostname_resolves(self.postgres_host):
            self.postgres_host = "localhost"
        if self.database_url:
            self.database_url = rewrite_unresolvable_compose_url(self.database_url)
        if self.app_env == "production":
            weak_secrets = {
                "INSECURE_DEV_ONLY_CHANGE_ME",
                "CHANGE_ME_GENERATE_A_LONG_RANDOM_SECRET",
                "dev-only-not-for-production",
            }
            if self.secret_key in weak_secrets or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a long random value in production")
            if self.seed_on_startup:
                raise ValueError("SEED_ON_STARTUP must be false in production")
        return self

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
