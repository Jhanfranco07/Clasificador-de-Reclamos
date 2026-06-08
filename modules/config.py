from __future__ import annotations

import os


APP_NAME = "SmartClaim AI"
APP_SUBTITLE = "Sistema inteligente para análisis, clasificación y respuesta de reclamos"
DEFAULT_AUTH_SECRET = "smartclaim-dev-secret-change-me"


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def cors_origins() -> list[str]:
    configured = [
        value.strip().rstrip("/")
        for value in ",".join([
            os.getenv("CORS_ORIGINS", ""),
            os.getenv("FRONTEND_URL", ""),
        ]).split(",")
        if value.strip()
    ]
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if not is_production():
        return list(dict.fromkeys(defaults + configured))
    return list(dict.fromkeys(["https://clasificador-de-reclamos.vercel.app"] + configured))


def allow_vercel_previews() -> bool:
    return os.getenv("ALLOW_VERCEL_PREVIEWS", "false").strip().lower() in {"1", "true", "yes", "on"}


def validate_runtime_config() -> None:
    if not is_production():
        return

    secret = os.getenv("AUTH_SECRET", "").strip()
    if not secret or secret == DEFAULT_AUTH_SECRET or len(secret) < 32:
        raise RuntimeError("AUTH_SECRET debe configurarse en producción con al menos 32 caracteres.")
    if not cors_origins() and not allow_vercel_previews():
        raise RuntimeError("Configura CORS_ORIGINS en producción con la URL del frontend.")
