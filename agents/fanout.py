import os, json, asyncio, redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from builtins import open as builtin_open

# alias built-in open so tests can monkeypatch this module's open()
open = builtin_open
from prometheus_client import Counter, Gauge, start_http_server

VALKEY = os.getenv("VALKEY_URL", "redis://valkey:6379")
TOPICS = ["politics","business","technology","sports","health",
          "climate","science","education","entertainment","finance"]
FEED_MAX_LEN = int(os.getenv("FEED_LEN", "100"))      # per-user feed length
TOPIC_MAX_LEN = int(os.getenv("TOPIC_MAXLEN", "10000"))  # topic stream length

IN  = Counter("fan_in_total",  "")
OUT = Counter("fan_out_total", "", ["topic"])
Q_LEN = Gauge("topic_stream_len", "Length of each topic stream", ["topic"])
FEED_PUSH = Counter("feed_push_total", "")
FEED_LEN = Gauge("feed_len", "", ["uid"])
TRIM_OPS = Gauge("topic_stream_trim_ops_total", "")
TOPIC_MAX_LEN_GAUGE = Gauge("topic_max_len", "Current trim length for topic streams")

# -------- helpers --------------------------------------------------
async def rconn():
    while True:
        try:
            r = await redis.from_url(VALKEY, decode_responses=True)
            await r.ping() ; return r
        except Exception:  await asyncio.sleep(1)

async def load_sha(r):
    lua = open("fanout.lua").read()
    return await r.script_load(lua)

# -------- main -----------------------------------------------------
async def main():
    start_http_server(9111)
    TOPIC_MAX_LEN_GAUGE.set(TOPIC_MAX_LEN)
    r   = await rconn()
    sha = await load_sha(r)
    consumer = "fan-1"

    # create consumer groups once
    for t in TOPICS:
        try:
            await r.xgroup_create(f"topic:{t}", f"cg_{t}", id="0", mkstream=True)
        except redis.ResponseError:
            pass  # already exists

    while True:
        try:
            for t in TOPICS:
                stream, grp = f"topic:{t}", f"cg_{t}"
                msgs = await r.xreadgroup(grp, consumer, {stream: ">"}, count=32, block=50)
                if not msgs:
                    continue
                for mid, f in msgs[0][1]:
                    if "data" in f:
                        try:
                            payload = json.loads(f["data"])
                        except Exception:
                            payload = {"summary": f["data"]}
                    else:
                        payload = f
                    summary = payload.get("summary") or payload.get("body", "")[:250]
                    payload["summary"] = summary
                    users = await r.zrange(f"user:topic:{t}", 0, -1)
                    await r.evalsha(
                        sha, 1, stream, mid, t, json.dumps(payload), FEED_MAX_LEN, TOPIC_MAX_LEN
                    )
                    TRIM_OPS.inc()
                    await r.xack(stream, grp, mid)
                    IN.inc(); OUT.labels(topic=t).inc()

                    if users:
                        pipe = r.pipeline()
                        for uid in users:
                            pipe.llen(f"feed:{uid}")
                        lengths = await pipe.execute()
                        for uid, ln in zip(users, lengths):
                            FEED_PUSH.inc()
                            FEED_LEN.labels(uid=uid).set(ln)

                Q_LEN.labels(topic=t).set(await r.xlen(stream))
            await asyncio.sleep(0.05)
        except (RedisConnError, redis.ResponseError):
            # reconnect or reload script if Valkey restarted
            r   = await rconn()
            sha = await load_sha(r)

if __name__ == "__main__":
    asyncio.run(main())

