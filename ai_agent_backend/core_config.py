from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env.local"), override=True)


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
    auto_seed: bool


def _resolve_data_path(value: str, default_name: str) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return os.path.join(BASE_DIR, default_name)
    if os.path.isabs(raw_value):
        return raw_value
    return os.path.normpath(os.path.join(BASE_DIR, raw_value))


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


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
        database_path=_resolve_data_path(
            os.getenv("STOCKQUERY_DB_PATH", ""),
            "agent_inventory.db",
        ),
        chroma_path=_resolve_data_path(
            os.getenv("STOCKQUERY_CHROMA_PATH", ""),
            "chroma_db",
        ),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        llm_api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        llm_model=os.getenv("STOCKQUERY_LLM_MODEL", "qwen2.5:1.5b"),
        llm_timeout_seconds=float(os.getenv("STOCKQUERY_LLM_TIMEOUT_SECONDS", "60")),
        low_stock_threshold=int(os.getenv("STOCKQUERY_LOW_STOCK_THRESHOLD", "10")),
        session_history_limit=int(os.getenv("STOCKQUERY_SESSION_HISTORY_LIMIT", "12")),
        cors_origins=origins,
        auto_seed=_env_flag("STOCKQUERY_AUTO_SEED", default=False),
    )
