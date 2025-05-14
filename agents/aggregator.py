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

from collections import defaultdict
PROC, STATS, WIN = "news_proc", "stats", 60
IN_MSG = Counter("aggregator_in_total", "Msgs in")
OUT_MSG = Counter("aggregator_out_total", "Buckets out")
async def flush(r, ts, bucket):
    k=f"bucket:{ts}"
    await r.json().set(k,"$",bucket); await r.xadd(STATS,{"bucket":k}); OUT_MSG.inc()
async def main():
    start_http_server(9103); r=await rconn()
    grp,cons="cg_agg","agg-1"
    try: await r.xgroup_create(PROC,grp,id="0",mkstream=True)
    except redis.ResponseError: pass
    start=int(time.time()//WIN*WIN)
    bucket=defaultdict(lambda:{"pos":0,"neg":0,"neu":0,"count":0})
    while True:
        res=await r.xreadgroup(grp,cons,{PROC:">"},count=256,block=1000)
        now=int(time.time())
        if res:
            for mid,f in res[0][1]:
                lbl=f["sentiment"].lower()
                lbl="pos" if lbl.startswith("pos") else "neg" if lbl.startswith("neg") else "neu"
                t=f["topic"]; bucket[t][lbl]+=1; bucket[t]["count"]+=1
                await r.xack(PROC,grp,mid); IN_MSG.inc()
        if now>=start+WIN:
            if any(v["count"] for v in bucket.values()): await flush(r,start,bucket)
            start=int(now//WIN*WIN); bucket=defaultdict(lambda:{"pos":0,"neg":0,"neu":0,"count":0})
if __name__=="__main__": asyncio.run(main())
