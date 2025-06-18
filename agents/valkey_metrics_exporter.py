from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, Any

import redis.asyncio as redis
from prometheus_client import (
    Gauge,
    Counter,
    Histogram,
    start_http_server,
)
from redis.exceptions import ConnectionError as RedisConnError

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
SCRAPE_PORT = 9121

# ────────────────────────────────── Prom metrics ───────────────────────────────
CLIENTS = Gauge("redis_connected_clients", "Number of connected clients")
MEM = Gauge("redis_memory_used_bytes", "Memory used (bytes)")
OPS = Counter("redis_commands_processed_total", "Total commands processed")
HITS = Counter("redis_keyspace_hits_total", "Keyspace hits")
MISSES = Counter("redis_keyspace_misses_total", "Keyspace misses")

# Histogram buckets match exporter-v2 defaults (in seconds)
LAT = Histogram(
    "redis_command_call_duration_seconds",
    "Rolling command latency histogram",
    buckets=(
        0.0001, 0.00025, 0.0005, 0.001,
        0.0025, 0.005, 0.01, 0.025,
        0.05, 0.1, 0.25, 0.5, 1.0
    ),
)

# ────────────────────────────────── helpers ────────────────────────────────────


async def connect() -> redis.Redis:
    """Retry until Valkey is reachable."""
    while True:
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)


def parse_info(info: Dict[str, Any]) -> None:
    """Update gauges/counters from INFO output."""
    CLIENTS.set(int(info.get("connected_clients", 0)))
    MEM.set(int(info.get("used_memory", 0)))
    OPS.inc(int(info.get("total_commands_processed", 0)) - OPS._value.get())
    HITS.inc(int(info.get("keyspace_hits", 0)) - HITS._value.get())
    MISSES.inc(int(info.get("keyspace_misses", 0)) - MISSES._value.get())


async def scrape(r: redis.Redis) -> None:
    """Collect INFO and LATENCY LATEST every second."""
    last_ops = 0
    last_hits = 0
    last_misses = 0
    while True:
        try:
            info = await r.info()
            parse_info(info)

            # LATENCY LATEST returns [[event, timestamp, microseconds, samples]]
            latest = await r.execute_command("LATENCY", "LATEST") or []
            for ev in latest:
                if ev and ev[0] == "command":
                    microseconds = int(ev[2])
                    LAT.observe(microseconds / 1e6)
                    break

            await asyncio.sleep(1)
        except RedisConnError:
            r = await connect()


async def main() -> None:
    start_http_server(SCRAPE_PORT)
    r = await connect()
    await scrape(r)


if __name__ == "__main__":
    asyncio.run(main())
