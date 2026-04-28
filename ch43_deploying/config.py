"""Production configuration loaded from environment variables (Chapter 38).

Copy .env.example to .env and edit before running locally.
In production, set variables via systemd EnvironmentFile or container env.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist (production behaviour)

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./minigithub.db",  # dev fallback only
)

SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
