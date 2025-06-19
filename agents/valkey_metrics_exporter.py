# ─────────────────────────────────────────────────────────────────────
#  Unified Valkey → Prometheus exporter
#  • Adds network byte counters  (in/out)
#  • Adds dataset memory gauge
#  • Keeps fragmentation, RSS, latency hist, etc.
# ─────────────────────────────────────────────────────────────────────
from __future__ import annotations
import asyncio
import os
import time
from typing import Dict, Any

import redis.asyncio as redis
from prometheus_client import (
    Counter, Gauge, Histogram, start_http_server,
)
from redis.exceptions import ConnectionError as RedisConnError

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
SCRAPE_PORT = int(os.getenv("SCRAPE_PORT", 9121))
PING_SAMPLES = int(os.getenv("LAT_PINGS_PER_LOOP", 5))

# ─── Core gauges ────────────────────────────────────────────────────
CLIENTS = Gauge("redis_connected_clients",        "Valkey connected clients")
MEM = Gauge("redis_memory_used_bytes",        "Memory used (bytes)")
MEM_RSS = Gauge("redis_memory_rss_bytes",         "Memory RSS (bytes)")
MEM_DATA = Gauge("redis_memory_dataset_bytes",     "Dataset size (bytes)")
FRAG = Gauge("redis_mem_fragmentation_ratio",  "Memory fragmentation ratio")

# ─── Counters ───────────────────────────────────────────────────────
OPS = Counter("redis_commands_processed_total",   "Commands processed")
HITS = Counter("redis_keyspace_hits_total",        "Keyspace hits")
MISSES = Counter("redis_keyspace_misses_total",      "Keyspace misses")
NET_IN = Counter("redis_net_input_bytes_total",      "Bytes read from clients")
NET_OUT = Counter("redis_net_output_bytes_total",
                  "Bytes written to clients")

# ─── Histogram (round‑trip ping latency) ────────────────────────────
LAT_HIST = Histogram(
    "redis_command_call_duration_seconds",
    "Round‑trip command latency",
    buckets=(
        0.00005, 0.0001, 0.00025, 0.0005,
        0.001, 0.0025, 0.005, 0.01,
        0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
    ),
)

_last: Dict[str, int] = dict()

# ─────────────────────────────────────────────────────────────────────


async def connect() -> redis.Redis:
    while True:
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)


def _inc(counter: Counter, key: str, new_val: int) -> None:
    delta = new_val - _last.get(key, 0)
    if delta >= 0:
        counter.inc(delta)
    _last[key] = new_val


async def scrape(r: redis.Redis) -> None:
    while True:
        try:
            info: Dict[str, Any] = await r.info()

            # Gauges
            CLIENTS.set(int(info["connected_clients"]))
            mem = int(info["used_memory"])
            mem_rss = int(info["used_memory_rss"])
            mem_data = int(info["used_memory_dataset"])
            MEM.set(mem)
            MEM_RSS.set(mem_rss)
            MEM_DATA.set(mem_data)
            FRAG.set(mem_rss / mem if mem else 0)

            # Counters (monotonic)
            _inc(OPS,   "ops",    int(info["total_commands_processed"]))
            _inc(HITS,  "hits",   int(info["keyspace_hits"]))
            _inc(MISSES, "misses", int(info["keyspace_misses"]))
            _inc(NET_IN, "net_in", int(info["total_net_input_bytes"]))
            _inc(NET_OUT, "net_out", int(info["total_net_output_bytes"]))

            # Latency histogram – measured, not sampled
            for _ in range(PING_SAMPLES):
                tic = time.perf_counter()
                await r.ping()
                LAT_HIST.observe(time.perf_counter() - tic)

            await asyncio.sleep(1)

        except RedisConnError:
            r = await connect()


async def main() -> None:
    start_http_server(SCRAPE_PORT)
    r = await connect()
    await scrape(r)

if __name__ == "__main__":
    asyncio.run(main())
