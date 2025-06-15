"""
Enrichment service (topic classification).

* Adds GPU‑utilisation gauge so the dashboard can show how many replicas
  actually run on CUDA.
* Keeps original functionality unchanged otherwise.
"""
from __future__ import annotations
import os, json, asyncio, time
from typing import List, Dict

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from transformers import pipeline
import torch

# ─────────────────────────────────────────
#  Device selection
# ─────────────────────────────────────────
USE_CUDA_ENV = os.getenv("ENRICH_USE_CUDA", "auto").lower()
if USE_CUDA_ENV == "1":
    DEVICE = 0
elif USE_CUDA_ENV == "0":
    DEVICE = -1
else:
    DEVICE = 0 if torch.cuda.is_available() else -1

#  Publish a one‑shot gauge that stays at 1 when running on GPU
GPU_GAUGE = Gauge(
    "enrich_gpu",
    "1 if this enrich replica is running on GPU; 0 otherwise",
)
GPU_GAUGE.set(1 if DEVICE >= 0 else 0)

# ─────────────────────────────────────────
VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
SOURCE = "news_raw"
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]
BATCH = int(os.getenv("ENRICH_BATCH", "32"))
NEWS_RAW_MAXLEN = int(os.getenv("NEWS_RAW_MAXLEN", "5000"))
TXT_CLF = 512  # characters fed to classifier

# ─────────────────────────────────────────
async def rconn() -> redis.Redis:
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)

classifier = pipeline(
    "zero-shot-classification",
    model="typeform/distilbert-base-uncased-mnli",
    device=DEVICE,
)
print(f"[enrich] classifier device={DEVICE}")

# ─────────────────────────────────────────
IN_MSG  = Counter("enrich_in_total",  "Raw messages consumed")
OUT_MSG = Counter("enrich_out_total", "Messages routed to topic streams", ["topic"])
LAT     = Histogram("enrich_classifier_latency_seconds", "Classification latency")
BACKLOG = Gauge("news_raw_len", "Length of news_raw stream")
TRIM_OPS = Gauge("news_raw_trim_ops_total", "Trimming operations on news_raw")

# ─────────────────────────────────────────

def classify(batch: List[Dict[str, str]]) -> List[Dict[str, str]]:
    texts = [d["title"] + " " + d["body"][:TXT_CLF] for d in batch]
    with LAT.time():
        results = classifier(texts, TOPICS, multi_label=False)
    for doc, res in zip(batch, results):
        doc["topic"] = res["labels"][0]
    return batch

# ─────────────────────────────────────────
async def main() -> None:
    start_http_server(9110)
    r = await rconn()

    grp, consumer = "cg_enrich", f"enrich-{os.getpid()}"
    try:
        await r.xgroup_create(SOURCE, grp, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # group may already exist

    buffer: List = []

    while True:
        try:
            msgs = await r.xreadgroup(grp, consumer, {SOURCE: ">"}, count=BATCH, block=500)
            if msgs:
                buffer.extend(msgs[0][1])

            if len(buffer) < BATCH:
                continue

            mids, raw_docs = zip(*buffer[:BATCH])
            buffer = buffer[BATCH:]

            docs = [
                {
                    "id": d["id"],
                    "title": d["title"],
                    "body": d.get("body", d.get("text", "")),
                }
                for d in raw_docs
            ]
            docs = classify(docs)

            pipe = r.pipeline()
            for d in docs:
                stream = f"topic:{d['topic']}"
                payload = json.dumps(
                    {
                        "id": d["id"],
                        "title": d["title"],
                        "summary": d.get("summary", ""),
                        "body": d.get("body", ""),
                        "tags": [d["topic"]],
                        "topic": d["topic"],
                    }
                )
                pipe.xadd(stream, {"data": payload})
                pipe.xtrim(stream, maxlen=10_000)
                OUT_MSG.labels(topic=d["topic"]).inc()
            await pipe.execute()

            #  Ack + trim source
            await r.xack(SOURCE, grp, *mids)
            await r.xtrim(SOURCE, maxlen=NEWS_RAW_MAXLEN, approximate=False)
            TRIM_OPS.inc()
            IN_MSG.inc(len(docs))
            BACKLOG.set(await r.xlen(SOURCE))

        except RedisConnError:
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())
