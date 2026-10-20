
import os
from dotenv import load_dotenv

# Load variables from backend/.env
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")
_DEV_SECRET = "dev-only-insecure-secret-do-not-use-in-production"
JWT_SECRET = os.getenv("JWT_SECRET", _DEV_SECRET)
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

_url = os.getenv("DATABASE_URL", "sqlite:///./agrichain.db")
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)
DATABASE_URL = _url

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
if APP_ENV == "production" and JWT_SECRET == _DEV_SECRET:
    raise RuntimeError("JWT_SECRET must be set in production")
