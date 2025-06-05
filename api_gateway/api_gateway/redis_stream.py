from __future__ import annotations

import json
import os
from typing import AsyncIterator, Any
import redis.asyncio as redis

from .stream import IStream

class RedisStream(IStream):
    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv("VALKEY_URL", "redis://localhost:6379")
        self._conn: redis.Redis | None = None

    async def _conn_ready(self) -> redis.Redis:
        if self._conn is None:
            self._conn = await redis.from_url(self.url, decode_responses=True)
        return self._conn

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        r = await self._conn_ready()
        if channel.startswith("topic:"):
            last_id = "$"
            while True:
                msgs = await r.xread({channel: last_id}, block=0, count=1)
                if not msgs:
                    continue
                _, entries = msgs[0]
                for entry_id, data in entries:
                    last_id = entry_id
                    payload = data.get("data")
                    if payload is None:
                        yield data
                    else:
                        try:
                            yield json.loads(payload)
                        except Exception:
                            yield payload
        elif channel.startswith("feed:"):
            while True:
                item = await r.brpop(channel, timeout=0)
                if item is None:
                    continue
                _, value = item
                try:
                    yield json.loads(value)
                except Exception:
                    yield value
        else:
            raise ValueError(f"unknown channel {channel}")
