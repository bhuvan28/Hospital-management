from pathlib import Path
from urllib.parse import urlparse

import pytest
from pydantic import ValidationError

from app.config import Settings, rewrite_unresolvable_compose_url


def test_default_postgres_host_is_localhost(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    settings = Settings(_env_file=None)
    assert settings.postgres_host == "localhost"
    assert urlparse(settings.sqlalchemy_database_uri).hostname == "localhost"


def test_compose_host_falls_back_when_unresolvable(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.config.hostname_resolves", lambda host: False)
    settings = Settings(_env_file=None)
    assert settings.postgres_host == "localhost"
    assert urlparse(settings.sqlalchemy_database_uri).hostname == "localhost"


def test_compose_host_kept_when_resolvable(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.config.hostname_resolves", lambda host: True)
    settings = Settings(_env_file=None)
    assert settings.postgres_host == "postgres"
    assert urlparse(settings.sqlalchemy_database_uri).hostname == "postgres"


def test_database_url_compose_host_falls_back(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://rmh:secret@postgres:5432/rmh_hctm",
    )
    monkeypatch.setattr("app.config.hostname_resolves", lambda host: False)
    settings = Settings(_env_file=None)
    parsed = urlparse(settings.sqlalchemy_database_uri)
    assert parsed.hostname == "localhost"
    assert parsed.port == 5432
    assert parsed.username == "rmh"
    assert parsed.password == "secret"
    assert parsed.path == "/rmh_hctm"


def test_rewrite_preserves_credentials_and_port(monkeypatch):
    monkeypatch.setattr("app.config.hostname_resolves", lambda host: False)
    rewritten = rewrite_unresolvable_compose_url("postgresql+psycopg://rmh:p%40ss@db:5433/app")
    parsed = urlparse(rewritten)
    assert parsed.hostname == "localhost"
    assert parsed.port == 5433
    assert parsed.username == "rmh"
    # Percent-encoding in the password is preserved so SQLAlchemy URLs stay valid.
    assert parsed.password in {"p@ss", "p%40ss"}
    assert "p%40ss" in rewritten


def test_env_example_uses_localhost_not_compose_dns():
    env_example = Path(__file__).resolve().parents[2] / ".env.example"
    text = env_example.read_text(encoding="utf-8")
    assert "POSTGRES_HOST=localhost" in text
    assert "POSTGRES_HOST=postgres" not in text
    assert "@localhost:5432/" in text
    assert "@postgres:5432/" not in text


def test_production_rejects_weak_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "short")
    monkeypatch.setenv("SEED_ON_STARTUP", "false")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_rejects_seed_on_startup(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 40)
    monkeypatch.setenv("SEED_ON_STARTUP", "true")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
