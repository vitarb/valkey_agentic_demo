import os, asyncio, time, json, random, warnings
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, start_http_server

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

POP = Counter("reader_pops_total","")

async def main():
    start_http_server(9112)
    r = await rconn()
    while True:
        try:
            lu = int(await r.get("latest_uid") or 0)
            if lu:
                uid = random.randint(0, lu)
                await r.brpop(f"feed:{uid}", timeout=1)
                POP.inc()
            await asyncio.sleep(0.5)
        except RedisConnError:
            r = await rconn()

if __name__=="__main__": asyncio.run(main())
