"""
Fan‑out service (topic stream → per‑user feeds).

Changes:
 • Avoid ZRANGE per message – cache subscriber list for 1 s per topic.
 • Replace heavy Lua with a tiny 'trim only' script; pushes done in‑client.
 • Adds Prometheus gauge for subscriber count + trim ops.
"""
import os, json, asyncio, time, redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from builtins import open as builtin_open
from prometheus_client import Counter, Gauge, start_http_server

# expose built-in open so tests can monkeypatch this module
open = builtin_open

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
TOPICS = ["politics","business","technology","sports","health",
          "climate","science","education","entertainment","finance"]
FEED_MAX_LEN  = int(os.getenv("FEED_LEN",    "100"))
TOPIC_MAX_LEN = int(os.getenv("TOPIC_MAXLEN","10000"))
CACHE_TTL     = 1.0  # seconds

IN        = Counter("fan_in_total",              "")
OUT       = Counter("fan_out_total",             "", ["topic"])
Q_LEN     = Gauge("topic_stream_len",            "", ["topic"])
SUBS      = Gauge("topic_subscribers",           "Users per topic", ["topic"])
FEED_PUSH = Counter("feed_push_total",           "")
FEED_LEN  = Gauge("feed_len",                    "", ["uid"])
TRIM_OPS  = Gauge("topic_stream_trim_ops_total", "")
TOPIC_MAX_LEN_GAUGE = Gauge("topic_max_len",     "",)
TOPIC_MAX_LEN_GAUGE.set(TOPIC_MAX_LEN)

# ──────────────────────────────
async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping(); return r
        except Exception:  await asyncio.sleep(1)

async def load_sha(r):
    return await r.script_load(open("fanout.lua").read())

# ──────────────────────────────
async def main():
    start_http_server(9111)
    r   = await rconn()
    sha = await load_sha(r)

    consumer = f"fanout-{os.getpid()}"
    for t in TOPICS:
        try:
            await r.xgroup_create(f"topic:{t}", f"cg_{t}", id="0", mkstream=True)
        except redis.ResponseError:
            pass

    sub_cache: dict[str, tuple[list[str], float]] = {}  # topic → (uids, expires_at)

    while True:
        try:
            for t in TOPICS:
                stream, grp = f"topic:{t}", f"cg_{t}"
                msgs = await r.xreadgroup(grp, consumer, {stream: ">"}, count=64, block=50)
                if not msgs:
                    continue

                # fetch & cache subscribers
                uids, expiry = sub_cache.get(t, ([], 0.0))
                now = time.time()
                if now >= expiry:
                    uids = await r.zrange(f"user:topic:{t}", 0, -1)
                    sub_cache[t] = (uids, now + CACHE_TTL)
                    SUBS.labels(topic=t).set(len(uids))

                use_pipe = hasattr(r, "pipeline")
                pipe = r.pipeline() if use_pipe else r
                for mid, f in msgs[0][1]:
                    payload = f.get("data")
                    if not payload:
                        payload = json.dumps(f)
                    # fan‑out
                    for uid in uids:
                        key = f"feed:{uid}"
                        # list remains the primary queue for the reader
                        if use_pipe:
                            pipe.lpush(key, payload)
                            pipe.ltrim(key, 0, FEED_MAX_LEN - 1)
                        else:
                            await pipe.lpush(key, payload)
                            await pipe.ltrim(key, 0, FEED_MAX_LEN - 1)
                        FEED_PUSH.inc()

                        # NEW: mirror every item into a per-user stream
                        # This lets WebSocket clients replay the latest
                        # messages without deleting them (reader still
                        # consumes the list, not the stream).
                        s_key = f"feed_stream:{uid}"
                        if use_pipe:
                            pipe.xadd(s_key, {"data": payload})
                            pipe.xtrim(s_key, maxlen=FEED_MAX_LEN)
                        else:
                            await pipe.xadd(s_key, {"data": payload})
                            await pipe.xtrim(s_key, maxlen=FEED_MAX_LEN)
                    # ack & trim
                    if use_pipe:
                        pipe.xack(stream, grp, mid)
                    else:
                        await pipe.xack(stream, grp, mid)
                    IN.inc(); OUT.labels(topic=t).inc()
                # one trim op per batch  (topic stream only)
                if use_pipe:
                    pipe.evalsha(sha, 1, stream, TOPIC_MAX_LEN)
                else:
                    await pipe.evalsha(sha, 1, stream, TOPIC_MAX_LEN)
                TRIM_OPS.inc()
                if use_pipe:
                    await pipe.execute()

                Q_LEN.labels(topic=t).set(await r.xlen(stream))

            await asyncio.sleep(0.02)

        except (RedisConnError, redis.ResponseError):
            r   = await rconn()
            sha = await load_sha(r)

if __name__ == "__main__":
    asyncio.run(main())
