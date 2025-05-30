import os
import asyncio
import redis.asyncio as redis
from prometheus_client import Gauge, start_http_server
from redis.exceptions import ConnectionError as RedisConnError

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
LAT_GAUGE = Gauge("redis_command_latency_usecs", "Latest command latency in microseconds")

async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)

async def main():
    start_http_server(9122)
    r = await rconn()
    while True:
        try:
            latest = await r.execute_command("LATENCY", "LATEST") or []
            for ev in latest:
                if ev and ev[0] == "command":
                    LAT_GAUGE.set(int(ev[2]))
                    break
            await asyncio.sleep(1)
        except RedisConnError:
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())
