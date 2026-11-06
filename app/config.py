"""Environment-driven settings. Everything secret lives in .env (git-ignored)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Does nothing if .env is missing; real environment variables always win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", encoding="utf-8-sig")


def get(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return default if value is None or value == "" else value


def get_int(name: str, default: int) -> int:
    try:
        return int(get(name, str(default)))
    except ValueError:
        return default


def flag(name: str) -> bool:
    return (get(name, "0") or "0").strip().lower() in ("1", "true", "yes", "on")
