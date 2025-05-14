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

import torch
from transformers import pipeline
CLS, PROC = "news_cls", "news_proc"
device = 0 if torch.cuda.is_available() else -1
model = pipeline("text-classification",
                 model="distilbert-base-uncased-finetuned-sst-2-english",
                 device=device)
IN_MSG = Counter("sentiment_in_total", "Msgs in")
OUT_MSG = Counter("sentiment_out_total", "Msgs out")
LAT = Histogram("sentiment_latency_seconds", "Model latency")

async def main():
    start_http_server(9102)
    r = await rconn()
    grp, cons = "cg_sent", "sent-1"
    try: await r.xgroup_create(CLS, grp, id="0", mkstream=True)
    except redis.ResponseError: pass
    while True:
        res = await r.xreadgroup(grp, cons, {CLS: ">"}, count=32, block=1000)
        if not res: continue
        for mid, f in res[0][1]:
            with LAT.time():
                res_label = model(f["body"])[0]
            f.update(sentiment=res_label["label"], confidence=float(res_label["score"]))
            await r.xadd(PROC, f)
            await r.xack(CLS, grp, mid)
            IN_MSG.inc(); OUT_MSG.inc()
if __name__ == "__main__":
    asyncio.run(main())
