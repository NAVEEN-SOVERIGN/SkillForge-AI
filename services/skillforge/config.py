
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = os.getenv("APP_ENV") == "production"
ORIGIN = os.getenv("APP_ORIGIN", "http://localhost:5173").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///" + str(ROOT / ".skillforge.db")
if DATABASE_URL.startswith(("postgresql://", "postgres://")):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.split("://", 1)[1]
if PRODUCTION and (not ORIGIN.startswith("https://") or not DATABASE_URL.startswith("postgresql+psycopg://")):
    raise RuntimeError("Production requires an HTTPS APP_ORIGIN and a PostgreSQL DATABASE_URL.")
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_CALLBACK = os.getenv("GITHUB_OAUTH_CALLBACK_URL", ORIGIN + "/api/auth/github/callback")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
JUDGE_URL = os.getenv("JUDGE_URL", "").rstrip("/")
JUDGE_TOKEN = os.getenv("JUDGE_TOKEN", "")
COOKIE = "__Host-skillforge" if PRODUCTION else "skillforge"
