import os
import asyncio
import time
import random
import warnings
import argparse
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")

async def rconn(retries=30, delay=1.0):
    "Retry until Valkey answers PING."
    for _ in range(retries):
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception as e:
            print("[common] Valkey not ready:", e)
            await asyncio.sleep(delay)
    raise RuntimeError("Valkey never became available")

POP = Counter("reader_pops_total", "")
POP_LAT = Histogram("reader_pop_latency_seconds", "")
FEED_LEN = Gauge("feed_len", "", ["uid"])
FEED_BACKLOG = Gauge("feed_backlog", "Total length of all feeds")
DEFAULT_RPS = 2.0

async def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--rps", type=float, default=DEFAULT_RPS)
    args = parser.parse_args([] if argv is None else argv)

    rps = float(os.getenv("READER_RPS", args.rps))
    delay = 1.0 / rps if rps > 0 else 0.5

    start_http_server(9112)
    r = await rconn()
    checked = 0
    last_debug = 0.0
    while True:
        try:
            lu = int(await r.get("latest_uid") or 0)
            backlog = 0
            if lu:
                uid = random.randint(0, lu)
                with POP_LAT.time():
                    item = await r.brpop(f"feed:{uid}", timeout=1)
                length_after = await r.llen(f"feed:{uid}")
                FEED_LEN.labels(uid=uid).set(length_after)
                for i in range(lu + 1):
                    backlog += await r.llen(f"feed:{i}")
                FEED_BACKLOG.set(backlog)
                if item is None:
                    now = time.time()
                    if now - last_debug >= 60:
                        print("[reader] no items for uid %s (total %d checked)" % (uid, checked))
                        last_debug = now
                else:
                    POP.inc()
                checked += 1
            else:
                FEED_BACKLOG.set(0)
            await asyncio.sleep(delay)
        except RedisConnError:
            r = await rconn()

if __name__=="__main__": asyncio.run(main())
