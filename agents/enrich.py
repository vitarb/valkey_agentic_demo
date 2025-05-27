"""
Fast-path enrichment (CPU-friendly)

• Tiny models
• Hard truncation
• Batched inference (8 docs)
• Sentiment step removed for now
"""

import os, asyncio, json
try:
    import torch
except Exception:  # pragma: no cover - torch may be missing in tests
    torch = None
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from transformers import pipeline

# ---------------- config -----------------
VALKEY   = os.getenv("VALKEY_URL", "redis://valkey:6379")
SOURCE   = "news_raw"
TOPICS   = ["politics","business","technology","sports","health",
            "climate","science","education","entertainment","finance"]
BATCH    = int(os.getenv("ENRICH_BATCH", "8"))      # docs per batch
TXT_CLF  = 512                                      # chars fed to classifier
TXT_SUM  = 256                                      # chars fed to summariser
SUM_LEN  = 40                                       # max summary tokens

# ---------------- redis helper -----------
async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)

# ---------------- tiny models ------------
CUDA = 0 if (torch and torch.cuda.is_available()) else -1
classifier = pipeline(
    "zero-shot-classification",
    model="typeform/distilbert-base-uncased-mnli",
    device=CUDA,
)
summariser_args = {
    "device": CUDA,
}
if torch:
    summariser_args["torch_dtype"] = (
        torch.float16 if CUDA == 0 else torch.float32
    )
summariser = pipeline(
    "summarization",
    model="philschmid/bart-tiny-cnn-6-6",
    **summariser_args,
)

# ---------------- metrics ----------------
IN   = Counter("enrich_in_total",  "")
OUT  = Counter("enrich_out_total", "")
CLS_LAT = Histogram("classifier_latency_seconds", "")
SUM_LAT = Histogram("summariser_latency_seconds", "")
NEWS_RAW_LEN = Gauge("news_raw_len", "Length of news_raw stream")

# ---------------- graph steps ------------
def pick_topic(batch):
    with CLS_LAT.time():
        texts = [d["title"] + " " + d["body"][:TXT_CLF] for d in batch]
        res   = classifier(texts, TOPICS, multi_label=False)
    for d, r in zip(batch, res):
        d["topic"] = r["labels"][0]
    return batch

def summarise(batch):
    with SUM_LAT.time():
        texts = [d["body"][:TXT_SUM] for d in batch]
        outs  = summariser(texts, max_length=SUM_LEN, truncation=True)
    for d, s in zip(batch, outs):
        d["summary"] = s["summary_text"]
    return batch

def enrich_docs(batch):
    batch = pick_topic(batch)
    batch = summarise(batch)
    return batch

# ---------------- main loop --------------
async def main():
    start_http_server(9110)
    r   = await rconn()
    grp = "cg_enrich"; consumer = "en-1"
    try:
        await r.xgroup_create(SOURCE, grp, id="0", mkstream=True)
    except redis.ResponseError:
        pass

    buffer = []              # holds (mid, fields) until we reach BATCH

    while True:
        try:
            msgs = await r.xreadgroup(grp, consumer, {SOURCE:">"},
                                      count=BATCH, block=500)
            if msgs:
                buffer.extend(msgs[0][1])

            if len(buffer) < BATCH:
                continue

            # split buffer
            batch_slice, buffer = buffer[:BATCH], buffer[BATCH:]
            mids, docs_raw = zip(*batch_slice)

            # map redis fields → plain dict
            docs = [{"id":d["id"], "title":d["title"], "body":d["text"]}
                    for d in docs_raw]

            # enrich docs without langgraph
            docs = enrich_docs(docs)

            pipe = r.pipeline()
            for d in docs:
                key = f"doc:{d['id']}"
                pipe.json().set(key,"$",d,nx=True).expire(key,86400)
                pipe.xadd(f"topic:{d['topic']}", {"id":d["id"],
                                                  "summary":d["summary"]})
                pipe.xtrim(f"topic:{d['topic']}", maxlen=10000)
            pipe.execute()

            # ack after successful write
            await r.xack(SOURCE, grp, *mids)
            IN.inc(len(docs)); OUT.inc(len(docs))
            NEWS_RAW_LEN.set(await r.xlen(SOURCE))

        except RedisConnError:
            r = await rconn()

if __name__ == "__main__":
    asyncio.run(main())

