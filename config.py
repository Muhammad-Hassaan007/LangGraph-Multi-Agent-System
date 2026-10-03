"""
Configuration module for the LangGraph Multi-Agent System.
Loads environment variables and exposes configuration settings cleanly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env", override=True)


def is_valid_secret(val: str) -> bool:
    """Checks whether a setting value is present and not an unconfigured placeholder."""
    if not val:
        return False
    v = val.strip().lower()
    placeholders = ["your_", "your-", "your_project", "placeholder", "sk-...", "https://your"]
    return not any(p in v for p in placeholders)


class Config:
    """Central configuration class accessible by all modules."""

    # LLM Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    
    # Models (checked against live Google API)
    GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.8-flash").strip()
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip()
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", GEMINI_CHAT_MODEL)

    # Supabase / Vector Store Settings
    _raw_url = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_URL = _raw_url.replace("/rest/v1/", "").replace("/rest/v1", "").rstrip("/")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or SUPABASE_KEY
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
    SUPABASE_TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "documents").strip() or "documents"

    # Embedding & RAG Settings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K = int(os.getenv("TOP_K", "5"))
    MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.3"))
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Karachi").strip()

    # GitHub MCP Settings
    GITHUB_PERSONAL_ACCESS_TOKEN = (
        os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
    ).strip()
    GITHUB_TOKEN = GITHUB_PERSONAL_ACCESS_TOKEN

    # Google Calendar Settings
    GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json")
    )
    GOOGLE_CALENDAR_TOKEN_PATH = os.getenv(
        "GOOGLE_CALENDAR_TOKEN_PATH", str(BASE_DIR / "token.json")
    )

    # Email Settings
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
    EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
    EMAIL_IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", 993))
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "").strip()
    EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").strip()

    @classmethod
    def is_supabase_configured(cls) -> bool:
        return is_valid_secret(cls.SUPABASE_URL) and is_valid_secret(cls.SUPABASE_KEY)

    @classmethod
    def is_llm_configured(cls) -> bool:
        return is_valid_secret(cls.OPENAI_API_KEY) or is_valid_secret(cls.GEMINI_API_KEY)


config = Config()
