"""
User‑feed reader – now *auto‑ramps* consumption when more users appear.

Changes
• Pops‑per‑second is no longer fixed; it grows linearly with `latest_uid`
  according to POP_RATE (default = 0.05 pops / user / sec) and is clamped
  by MAX_RPS.
• New Prometheus gauges:
    – reader_target_rps        (current calculated throughput goal)
    – avg_feed_backlog         (feed_backlog / latest_uid)
• Keeps the existing reader_pops_total and latency histogram so existing
  panels stay valid.
"""
from __future__ import annotations
import os
import argparse
import asyncio
import random
import time
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")

# ─── Auto‑scaling knobs ──────────────────────────────────────────────
POP_RATE = float(os.getenv("POP_RATE", 0.05))          # pops per user per sec
MAX_RPS = float(os.getenv("MAX_READER_RPS", 200.0))   # safety cap

# ─── Prometheus metrics ──────────────────────────────────────────────
POP = Counter("reader_pops_total",            "Successful feed pops")
POP_LAT = Histogram("reader_pop_latency_seconds", "BLPOP latency")
FEED_LEN = Gauge("feed_len",                       "Feed length", ["uid"])
FEED_BACK = Gauge("feed_backlog",
                  "Total backlog across feeds")
TARGET_RPS = Gauge("reader_target_rps",              "Dynamic target pops/s")
AVG_BACK = Gauge("avg_feed_backlog",               "Mean backlog / user")

# ─── Helpers ─────────────────────────────────────────────────────────


async def rconn(retries=30, delay=1.0) -> redis.Redis:
    for _ in range(retries):
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(delay)
    raise RuntimeError("Valkey unavailable")

# ─── Main loop ───────────────────────────────────────────────────────


async def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--rps", type=float, default=None, help="Fixed pops per second")
    args = parser.parse_args([] if argv is None else argv)

    fixed_rps = args.rps
    env_rps = os.getenv("READER_RPS")
    if env_rps is not None:
        try:
            fixed_rps = float(env_rps)
        except ValueError:
            fixed_rps = None

    start_http_server(9112)
    r = await rconn()
    backlog_total = 0
    last_calc = 0.0                         # next time we recompute the target
    delay = 1.0

    while True:
        try:
            # ── recompute target RPS once per second ─────────────────
            now = time.time()
            if now >= last_calc:
                latest_uid = int(await r.get("latest_uid") or 0)
                if fixed_rps and fixed_rps > 0:
                    target_rps = fixed_rps
                else:
                    target_rps = min(MAX_RPS, max(1.0, latest_uid * POP_RATE))
                delay = 1.0 / target_rps
                TARGET_RPS.set(target_rps)
                AVG_BACK.set(backlog_total / latest_uid if latest_uid else 0)
                last_calc = now + 1.0

            # ── pick user & consume ──────────────────────────────────
            uid = random.randint(0, latest_uid) if latest_uid else 0
            key = f"feed:{uid}"

            with POP_LAT.time():
                item = await r.brpop(key, timeout=1)
            if item:
                backlog_total -= 1
                POP.inc()

            length_after = await r.llen(key)
            backlog_total += length_after
            FEED_LEN.labels(uid=uid).set(length_after)
            FEED_BACK.set(max(0, backlog_total))

            await asyncio.sleep(delay)

        except RedisConnError:
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())
