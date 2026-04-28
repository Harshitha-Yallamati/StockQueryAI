from __future__ import annotations

import json
from typing import Iterator


def format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def iter_text_chunks(text: str, chunk_size: int = 80) -> Iterator[str]:
    cleaned = text.strip()
    if not cleaned:
        return
    for start in range(0, len(cleaned), chunk_size):
        yield cleaned[start : start + chunk_size]
