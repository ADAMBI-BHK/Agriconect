"""Configuration par variables d'environnement (voir .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_env = BASE_DIR / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DEFAULT_SECRET = "change-me-in-production"


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "oui")


class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./agriconnect.db")
    secret_key = os.getenv("SECRET_KEY", DEFAULT_SECRET)
    cookie_secure = _bool("COOKIE_SECURE")
    session_hours = int(os.getenv("SESSION_HOURS", "24"))
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    admin_email = os.getenv("ADMIN_EMAIL", "")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    app_url = os.getenv("APP_URL", "http://localhost:3000").rstrip("/")
    activation_days = int(os.getenv("ACTIVATION_DAYS", "7"))
    reset_password_hours = int(os.getenv("RESET_PASSWORD_HOURS", "2"))
    upload_dir = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "5"))
    max_list_rows = int(os.getenv("MAX_LIST_ROWS", "1000"))
    # Paiements : « demo » = simulation clairement identifiée, aucun argent réel.
    payment_mode = os.getenv("PAYMENT_MODE", "demo").lower()
    payment_provider = os.getenv("PAYMENT_PROVIDER", "demo").lower()
    payment_api_key = os.getenv("PAYMENT_API_KEY", "")
    payment_webhook_secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
    billing_enabled = _bool("BILLING_ENABLED", "true")
    # Courriel (facultatif) : sans SMTP_HOST, les invitations sont affichées/exportées par l'administration.
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "AgriConnect <no-reply@agriconnect.local>")
    seed_demo = _bool("SEED_DEMO")


settings = Settings()

if settings.cookie_secure and settings.secret_key == DEFAULT_SECRET:
    raise RuntimeError("SECRET_KEY par défaut interdit en production (COOKIE_SECURE=true).")
if settings.cookie_secure and settings.payment_mode == "demo":
    # Pas bloquant (une démo publique est possible) mais l'API le signalera clairement à l'interface.
    pass
