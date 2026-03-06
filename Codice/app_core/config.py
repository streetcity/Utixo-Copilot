from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv(BASE_DIR / ".env")


def _parse_admin_users(raw: str | None) -> set[str]:
    value = raw or "admin"
    return {item.strip() for item in value.split(",") if item.strip()}


def load_config() -> dict:
    return {
        "BASE_DIR": str(BASE_DIR),
        "STATIC_DIR": str(STATIC_DIR),
        "TEMPLATES_DIR": str(TEMPLATES_DIR),
        "SECRET_KEY": os.getenv("SECRET_KEY", "CHANGE_ME_PLEASE"),
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=int(os.getenv("ADMIN_SESSION_HOURS", "12"))),
        "DB_HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
        "DB_NAME": os.getenv("DB_NAME", "chatbot"),
        "DB_PORT": int(os.getenv("DB_PORT", "3306")),
        "SIM_THRESHOLD": float(os.getenv("SIM_THRESHOLD", "0.25")),
        "SIM_ALPHA_WORD": float(os.getenv("SIM_ALPHA_WORD", "0.65")),
        "SIM_LOW_HINT": float(os.getenv("SIM_LOW_HINT", "0.12")),
        "SUGGEST_TOPK": int(os.getenv("SUGGEST_TOPK", "3")),
        "TICKET_URL": os.getenv(
            "TICKET_URL",
            "https://shop.serverweb.net/submitticket.php?step=2&deptid=2",
        ),
        "HUMANIZE_ENABLED": os.getenv("HUMANIZE_ENABLED", "1").strip() == "1",
        "HUMANIZE_MIN_CHARS": int(os.getenv("HUMANIZE_MIN_CHARS", "30")),
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip(),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct").strip(),
        "OLLAMA_ENABLED": os.getenv("OLLAMA_ENABLED", "1").strip() == "1",
        "OLLAMA_TIMEOUT": float(os.getenv("OLLAMA_TIMEOUT", "20")),
        "OLLAMA_TEMPERATURE": float(os.getenv("OLLAMA_TEMPERATURE", "0.15")),
        "OLLAMA_MAX_TOKENS": int(os.getenv("OLLAMA_MAX_TOKENS", "220")),
        "OLLAMA_KEEP_ALIVE": os.getenv("OLLAMA_KEEP_ALIVE", "5m").strip(),
        "ADMIN_USERS": _parse_admin_users(os.getenv("ADMIN_USERS", "admin")),
        "PORT": int(os.getenv("PORT", "5000")),
        "DEBUG": os.getenv("FLASK_DEBUG", "1").strip() == "1",
    }