from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(__file__)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    database_path: str
    chroma_path: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: float
    low_stock_threshold: int
    session_history_limit: int
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "STOCKQUERY_CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://localhost:8081",
        ).split(",")
        if origin.strip()
    )
    return Settings(
        app_name="StockQuery AI Agent Backend",
        app_version="2.0.0",
        database_path=os.getenv(
            "STOCKQUERY_DB_PATH",
            os.path.join(BASE_DIR, "agent_inventory.db"),
        ),
        chroma_path=os.getenv(
            "STOCKQUERY_CHROMA_PATH",
            os.path.join(BASE_DIR, "chroma_db"),
        ),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        llm_api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        llm_model=os.getenv("STOCKQUERY_LLM_MODEL", "qwen2.5:1.5b"),
        llm_timeout_seconds=float(os.getenv("STOCKQUERY_LLM_TIMEOUT_SECONDS", "12")),
        low_stock_threshold=int(os.getenv("STOCKQUERY_LOW_STOCK_THRESHOLD", "10")),
        session_history_limit=int(os.getenv("STOCKQUERY_SESSION_HISTORY_LIMIT", "12")),
        cors_origins=origins,
    )
