"""Configuration objects, resolved from the environment.

Nothing here carries a usable production default: SECRET_KEY and JWT_SECRET_KEY
have dev-only fallbacks that ProductionConfig refuses to start with. That is
deliberate — this is the auth core, and a silently-defaulted signing key is the
exact class of bug that survives review because everything still "works".
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Dev-only sentinels. ProductionConfig.validate() rejects them.
_DEV_SECRET = "dev-only-insecure-secret-change-me"
_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", _DEV_SECRET)

    # --- Database ---------------------------------------------------------
    # SQLite for local dev; set DATABASE_URL to a postgresql:// URI to move.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'omnicare.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- JWT --------------------------------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEV_JWT_SECRET)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_DAYS", "14"))
    )
    JWT_ERROR_MESSAGE_KEY = "message"

    # --- CORS -------------------------------------------------------------
    # Explicit allowlist. Never "*" — credentialed requests would be rejected
    # by the browser anyway, and a wildcard hides that mistake until later.
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]

    @classmethod
    def validate(cls):
        """Hook for subclasses; base config permits dev defaults."""


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def validate(cls):
        weak = []
        if cls.SECRET_KEY == _DEV_SECRET:
            weak.append("SECRET_KEY")
        if cls.JWT_SECRET_KEY == _DEV_JWT_SECRET:
            weak.append("JWT_SECRET_KEY")
        if weak:
            raise RuntimeError(
                "Refusing to start in production with dev signing keys: "
                + ", ".join(weak)
                + ". Set them in the environment."
            )


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return CONFIGS.get(name, DevelopmentConfig)
