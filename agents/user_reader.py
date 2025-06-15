"""
User feed reader – pops items at a steady RPS.

* Replaces O(U) backlog scan with a rolling counter updated
  only when we push / pop.
"""
import os, asyncio, random, time
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
DEFAULT_RPS = 2.0

POP        = Counter("reader_pops_total", "")
POP_LAT    = Histogram("reader_pop_latency_seconds", "")
FEED_LEN   = Gauge("feed_len",              "", ["uid"])
FEED_BACK  = Gauge("feed_backlog",          "Total length of all feeds")

async def rconn(retries=30, delay=1.0):
    for _ in range(retries):
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(delay)
    raise RuntimeError("Valkey unavailable")

async def main(argv=None):
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--rps", type=float, default=DEFAULT_RPS)
    args = parser.parse_args([] if argv is None else argv)

    rps = float(os.getenv("READER_RPS", args.rps))
    delay = 1.0 / rps if rps > 0 else 0.5

    start_http_server(9112)
    r = await rconn()
    backlog_total = 0

    while True:
        try:
            lu = int(await r.get("latest_uid") or 0)
            if lu == 0:
                FEED_BACK.set(0)
                await asyncio.sleep(delay)
                continue

            uid = random.randint(0, lu)
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
