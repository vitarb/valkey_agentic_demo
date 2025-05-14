import asyncio, json, os, random, time
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, start_http_server

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
REDIS = None
async def rconn():
    global REDIS
    if REDIS is None or REDIS.closed:
        REDIS = await redis.from_url(VALKEY_URL, decode_responses=True)
    return REDIS

STREAM = "news_raw"
ARTICLES = [{"title": f"Article {i}", "body": "Lorem ipsum"} for i in range(1000)]
THROUGHPUT = int(os.getenv("THROUGHPUT", "1000"))
METRIC = Counter("fetcher_messages_total", "Articles fetched")

async def main():
    start_http_server(9100)
    r = await rconn()
    idx = 0
    while True:
        start = time.time()
        for _ in range(THROUGHPUT):
            art = ARTICLES[idx % len(ARTICLES)].copy()
            art["id"] = idx
            await r.xadd(STREAM, art)
            METRIC.inc(); idx += 1
        await asyncio.sleep(max(0, 1 - (time.time() - start)))
if __name__ == "__main__":
    asyncio.run(main())
