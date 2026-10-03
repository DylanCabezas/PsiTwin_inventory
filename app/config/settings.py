# app/config/settings.py

from functools import lru_cache

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)


class Settings(BaseSettings):

    # ============================================================
    # APLICACION
    # ============================================================

    app_name: str = "PsiTwin Inventory API"

    api_prefix: str = "/api/v1"


    # ============================================================
    # MONGODB
    # ============================================================

    mongodb_url: str = "mongodb://localhost:27017"

    mongodb_database: str = "psitwin_inventory"


    # ============================================================
    # SEGURIDAD
    # ============================================================

    secret_key: str = (
        "psitwin-secret-key-cambiar-en-produccion"
    )

    algorithm: str = "HS256"

    access_token_expire_minutes: int = 60

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    frontend_url: str | None = None
    email_verification_ttl_minutes: int = 10
    email_verification_cooldown_seconds: int = 60
    email_verification_max_attempts: int = 5


    # ============================================================
    # ENV
    # ============================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:

    return Settings()


# ================================================================
# INSTANCIA GLOBAL
#
# Permite usar:
#
# from app.config.settings import settings
#
# además de:
#
# settings = get_settings()
# ================================================================

settings = get_settings()