from __future__ import annotations

import os
from datetime import datetime, timezone
import redis.asyncio as redis

def redis_client() -> redis.Redis:
    return redis.Redis(host=os.getenv("VALKEY_HOST", "localhost"), decode_responses=True)


def reltime(raw_id: str) -> str:
    """Convert Valkey stream entry-id to human-friendly relative time."""
    try:
        ms = int(raw_id.split("-")[0])
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        delta = (datetime.now(timezone.utc) - dt).total_seconds()
        if delta < 90:
            return f"{int(delta)} s ago"
        if delta < 5400:
            return f"{int(delta/60)} m ago"
        if delta < 172800:
            return f"{int(delta/3600)} h ago"
        return dt.strftime("%d %b")
    except Exception:
        return ""
