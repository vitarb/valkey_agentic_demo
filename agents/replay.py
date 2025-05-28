import os, csv, asyncio, redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, start_http_server

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
CSV    = os.getenv("REPLAY_FILE", "data/news_sample.csv")
RPS    = float(os.getenv("REPLAY_RATE", "250"))

MSG = Counter("producer_msgs_total", "")

async def redis_ready():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping(); return r
        except Exception: await asyncio.sleep(1)

async def main():
    start_http_server(9114)           # expose producer counter
    csv_path = os.getenv("REPLAY_FILE", CSV)
    try:
        fp = open(csv_path, newline="", encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"[replay] '{csv_path}' missing in container")

    reader = csv.DictReader(fp)
    r = await redis_ready()

    for row in reader:
        try:
            await r.xadd("news_raw", {
                "id": row["id"], "title": row["title"], "text": row["text"]
            })
            MSG.inc()
        except RedisConnError:
            r = await redis_ready()
            continue
        await asyncio.sleep(1 / RPS)

if __name__ == "__main__":
    asyncio.run(main())

