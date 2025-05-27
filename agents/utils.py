from __future__ import annotations

import os
import redis.asyncio as redis

def redis_client() -> redis.Redis:
    return redis.Redis(host=os.getenv("VALKEY_HOST", "localhost"), decode_responses=True)
