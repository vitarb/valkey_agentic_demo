"""
Fan‑out service (topic stream → per‑user feeds)

Changes
• **De‑duplication** – Each user sees a given article ID only once.
  Uses a Redis SET feed_seen:<uid> with 24 h TTL; if SADD returns 0 the
  push is skipped.

• Adds Prometheus counter `fanout_duplicates_skipped_total` so you can
  chart de‑dupe effectiveness (see Grafana patch).

Everything else (batching, trim ops, caching) unchanged.
"""
import os
import json
import asyncio
import time
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, Gauge, start_http_server

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
TOPICS = ["politics", "business", "technology", "sports", "health",
          "climate", "science", "education", "entertainment", "finance"]
FEED_MAX_LEN = int(os.getenv("FEED_LEN",    "100"))
TOPIC_MAX_LEN = int(os.getenv("TOPIC_MAXLEN", "10000"))
CACHE_TTL = 1.0  # seconds
SEEN_TTL = 24*3600  # one day

IN = Counter("fan_in_total",  "Topic messages consumed")
OUT = Counter("fan_out_total", "Messages pushed", ["topic"])
DUP_SKIP = Counter("fanout_duplicates_skipped_total",
                   "Duplicate posts skipped")
Q_LEN = Gauge("topic_stream_len",     "", ["topic"])
SUBS = Gauge("topic_subscribers",    "", ["topic"])
FEED_PUSH = Counter("feed_push_total",    "")
FEED_LEN = Gauge("feed_len",             "", ["uid"])
TRIM_OPS = Gauge("topic_stream_trim_ops_total", "")
TOPIC_MAX_LEN_GAUGE = Gauge("topic_max_len", "")
TOPIC_MAX_LEN_GAUGE.set(TOPIC_MAX_LEN)

# ───────────────────────── helpers ────────────────────────────────


async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping()
            return r
        except Exception:
            await asyncio.sleep(1)


async def load_sha(r):
    lua = "redis.call('XTRIM', KEYS[1], 'MAXLEN', tonumber(ARGV[1])); return 1"
    return await r.script_load(lua)

# ───────────────────────── main loop ──────────────────────────────


async def main():
    start_http_server(9111)
    r = await rconn()
    sha = await load_sha(r)

    consumer = f"fanout-{os.getpid()}"
    for t in TOPICS:
        try:
            await r.xgroup_create(f"topic:{t}", f"cg_{t}", id="0", mkstream=True)
        except redis.ResponseError:
            pass

    sub_cache: dict[str, tuple[list[str], float]] = {}

    while True:
        try:
            for t in TOPICS:
                stream, grp = f"topic:{t}", f"cg_{t}"
                msgs = await r.xreadgroup(grp, consumer, {stream: ">"}, count=64, block=50)
                if not msgs:
                    continue

                # refresh subscriber list once per CACHE_TTL
                uids, expiry = sub_cache.get(t, ([], 0.0))
                now = time.time()
                if now >= expiry:
                    uids = await r.zrange(f"user:topic:{t}", 0, -1)
                    sub_cache[t] = (uids, now + CACHE_TTL)
                    SUBS.labels(topic=t).set(len(uids))

                for mid, f in msgs[0][1]:
                    payload = f.get("data") or json.dumps(f)
                    doc = json.loads(payload)
                    doc_id = doc.get("id")  # may be str or int

                    for uid in uids:
                        seen_key = f"feed_seen:{uid}"
                        # SADD returns 1 when the member wasn't present
                        added = await r.sadd(seen_key, doc_id)
                        if added == 0:      # duplicate
                            DUP_SKIP.inc()
                            continue
                        # expire lazily only on first insert
                        await r.expire(seen_key, SEEN_TTL, nx=True)

                        list_key = f"feed:{uid}"
                        stream_key = f"feed_stream:{uid}"

                        pipe = r.pipeline()
                        pipe.lpush(list_key, payload)
                        pipe.ltrim(list_key, 0, FEED_MAX_LEN - 1)
                        pipe.xadd(stream_key, {"data": payload})
                        pipe.xtrim(stream_key, maxlen=FEED_MAX_LEN)
                        await pipe.execute()

                        FEED_PUSH.inc()
                        FEED_LEN.labels(uid=uid).set(
                            await r.llen(list_key)
                        )

                    # ack & trim topic stream
                    await r.xack(stream, grp, mid)
                    await r.evalsha(sha, 1, stream, TOPIC_MAX_LEN)
                    TRIM_OPS.inc()
                    IN.inc()
                    OUT.labels(topic=t).inc()

                Q_LEN.labels(topic=t).set(await r.xlen(stream))
            await asyncio.sleep(0.02)

        except (RedisConnError, redis.ResponseError):
            r = await rconn()
            sha = await load_sha(r)

if __name__ == "__main__":
    asyncio.run(main())
