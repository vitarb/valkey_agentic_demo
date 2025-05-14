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

RAW, CLS = "news_raw", "news_cls"
TOPICS = ["tech", "politics", "health", "sports"]
IN_MSG = Counter("classifier_in_total", "Msgs in")
OUT_MSG = Counter("classifier_out_total", "Msgs out")
LAT = Histogram("classifier_latency_seconds", "Latency")

async def main():
    start_http_server(9101)
    r = await rconn()
    grp, cons = "cg_cls", "cls-1"
    try: await r.xgroup_create(RAW, grp, id="0", mkstream=True)
    except redis.ResponseError: pass
    while True:
        res = await r.xreadgroup(grp, cons, {RAW: ">"}, count=100, block=1000)
        if not res: continue
        for mid, f in res[0][1]:
            with LAT.time():
                f["topic"] = random.choice(TOPICS)
                await r.xadd(CLS, f); OUT_MSG.inc()
            await r.xack(RAW, grp, mid); IN_MSG.inc()
if __name__ == "__main__":
    asyncio.run(main())
