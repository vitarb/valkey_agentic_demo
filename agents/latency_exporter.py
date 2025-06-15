"""Expose Redis LATENCY LATEST as a Prometheus histogram."""
import os, asyncio, time
import redis.asyncio as redis
from prometheus_client import Histogram, start_http_server
from redis.exceptions import ConnectionError as RedisConnError

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
LAT = Histogram(
    "redis_command_latency_seconds",
    "Latency per Redis command (rolling)",
    buckets=[0.0001,0.0002,0.0005,0.001,0.002,0.005,0.01,0.02,0.05]
)

async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping(); return r
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
                    us = int(ev[2])
                    LAT.observe(us / 1e6)
                    break
            await asyncio.sleep(1)
        except RedisConnError:
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())
