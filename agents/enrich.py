"""
Enrichment -- topic classification only
───────────────────────────────────────
Reads raw articles from `news_raw`, assigns a single topic and publishes the
article ID + title to the corresponding `topic:<T>` stream so that the fan-out
service can deliver it to user feeds.

Environment variables:
    ENRICH_BATCH – articles processed per batch (default: 32)

Tiny DistilBERT-MNLI is still used because it is reasonably fast even on CPU,
but you can swap it out for a simpler heuristic if desired.
"""
from __future__ import annotations
import os
import json
import asyncio
from typing import List, Dict

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from transformers import pipeline

# ────────── Configuration ─────────────────────────────────────────
VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
SOURCE = "news_raw"
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]
BATCH = int(os.getenv("ENRICH_BATCH", "32"))   # articles per batch
TXT_CLF = 512                                  # characters fed to classifier

# ────────── Lazy Redis connection helper ──────────────────────────
async def rconn() -> redis.Redis:
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)

# ────────── Lightweight zero-shot classifier ──────────────────────
classifier = pipeline(
    "zero-shot-classification",
    model="typeform/distilbert-base-uncased-mnli",
    device=-1,                 # CPU only (change to 0 for CUDA)
)

# ────────── Metrics ───────────────────────────────────────────────
IN_MSG  = Counter("enrich_in_total",  "Raw messages consumed")
OUT_MSG = Counter("enrich_out_total", "Messages routed to topic streams")
LAT     = Histogram("enrich_classifier_latency_seconds", "Classification latency")
BACKLOG = Gauge("news_raw_len", "Length of news_raw stream")

# ────────── Helper ────────────────────────────────────────────────
def classify(batch: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Add a 'topic' field to each dict in *batch*."""
    texts = [d["title"] + " " + d["body"][:TXT_CLF] for d in batch]
    with LAT.time():
        results = classifier(texts, TOPICS, multi_label=False)
    for doc, res in zip(batch, results):
        doc["topic"] = res["labels"][0]
    return batch

# ────────── Main loop ─────────────────────────────────────────────
async def main() -> None:
    start_http_server(9110)
    r = await rconn()

    grp, consumer = "cg_enrich", "enrich-1"
    try:
        await r.xgroup_create(SOURCE, grp, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # group already exists

    buffer: List = []

    while True:
        try:
            msgs = await r.xreadgroup(grp, consumer, {SOURCE: ">"}, count=BATCH, block=500)
            if msgs:
                buffer.extend(msgs[0][1])

            if len(buffer) < BATCH:
                continue

            # Split & map Redis fields to plain dicts ---------------------------------
            batch_slice, buffer = buffer[:BATCH], buffer[BATCH:]
            mids, raw_docs = zip(*batch_slice)
            docs = [
                {
                    "id": d["id"],
                    "title": d["title"],
                    "body": d.get("body", d.get("text", "")),
                }
                for d in raw_docs
            ]

            # Classify & publish ------------------------------------------------------
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
            await pipe.execute()

            # Acknowledge and record metrics -----------------------------------------
            await r.xack(SOURCE, grp, *mids)
            IN_MSG.inc(len(docs))
            OUT_MSG.inc(len(docs))
            BACKLOG.set(await r.xlen(SOURCE))

        except RedisConnError:
            # Valkey went away – reconnect
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())

