from fastapi import FastAPI, WebSocket, Depends
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import json
import redis.asyncio as redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rdb
    if rdb is None:
        rdb = await redis.from_url(
            os.getenv("VALKEY_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
    yield

app = FastAPI(lifespan=lifespan)

# ──────────────────────────────  CORS  ──────────────────────────────
# The React UI is served from port 8500 while the API listens on 8000,
# which makes them different *origins* in the browser’s eyes.  Without
# the appropriate `Access‑Control‑Allow‑Origin` header every `fetch()`
# to `/user/{uid}` is blocked, so the “Interests” widget never appears.
#
# A permissive wildcard is fine for a local demo; tighten it or switch
# to an explicit domain list in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


rdb = None


def get_rdb():
    assert rdb is not None, "Redis not configured"
    return rdb


@app.get("/user/{uid}")
async def user(uid: str, r=Depends(get_rdb)):
    data = await r.json().get(f"user:{uid}")
    if not data:
        return {"interests": []}
    return {"interests": data.get("interests", [])}


@app.websocket("/ws/feed/{uid}")
async def feed_ws(
    ws: WebSocket,
    uid: str,
    backlog: int = 100,
    r=Depends(get_rdb),
):
    await ws.accept()
    # We now stream from the *immutable* per-user stream produced by fan-out
    # instead of popping the feed list (which the reader service consumes).
    stream = f"feed_stream:{uid}"
    try:
        # –– backlog (latest → oldest, capped by ?backlog=N) –––––––––
        entries = await r.xrevrange(stream, "+", "-", count=backlog)
        for _id, data in reversed(entries):
            payload = data.get("data") or data
            await ws.send_json(json.loads(payload) if isinstance(payload, str) else payload)

        # –– live tail using XREAD –––––––––––––––––
        last_id = "$"
        while True:
            msgs = await r.xread({stream: last_id}, block=0, count=1)
            if not msgs:
                continue
            _, entries = msgs[0]
            for _id, data in entries:
                last_id = _id
                payload = data.get("data") or data
                await ws.send_json(json.loads(payload) if isinstance(payload, str) else payload)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/topic/{slug}")
async def topic_ws(
    ws: WebSocket,
    slug: str,
    backlog: int = 50,
    r=Depends(get_rdb),
):
    await ws.accept()
    key = f"topic:{slug}"
    try:
        entries = await r.xrevrange(key, "+", "-", count=backlog)
        for _id, data in reversed(entries):
            payload = data.get("data")
            if payload is None:
                await ws.send_json(data)
            else:
                try:
                    await ws.send_json(json.loads(payload))
                except Exception:
                    await ws.send_json(payload)
        last_id = "$"
        while True:
            msgs = await r.xread({key: last_id}, block=0, count=1)
            if not msgs:
                continue
            _, entries = msgs[0]
            for _id, data in entries:
                last_id = _id
                payload = data.get("data")
                if payload is None:
                    await ws.send_json(data)
                else:
                    try:
                        await ws.send_json(json.loads(payload))
                    except Exception:
                        await ws.send_json(payload)
    except WebSocketDisconnect:
        pass
