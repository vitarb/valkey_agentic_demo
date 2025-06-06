from fastapi import FastAPI, WebSocket, Depends
from starlette.websockets import WebSocketDisconnect
import os
import json
import redis.asyncio as redis

app = FastAPI()

rdb = None

@app.on_event("startup")
async def init_redis():
    global rdb
    if rdb is None:
        rdb = await redis.from_url(os.getenv("VALKEY_URL", "redis://localhost:6379"), decode_responses=True)

def get_rdb():
    assert rdb is not None, "Redis not configured"
    return rdb

@app.get("/user/{uid}")
async def user(uid: str, r = Depends(get_rdb)):
    data = await r.json().get(f"user:{uid}")
    if not data:
        return {"interests": []}
    return {"interests": data.get("interests", [])}

@app.websocket("/ws/feed/{uid}")
async def feed_ws(
    ws: WebSocket,
    uid: str,
    backlog: int = 100,
    r = Depends(get_rdb),
):
    await ws.accept()
    key = f"feed:{uid}"
    try:
        entries = await r.lrange(key, 0, backlog - 1)
        for payload in reversed(entries):
            try:
                await ws.send_json(json.loads(payload))
            except Exception:
                await ws.send_json(payload)
        while True:
            result = await r.brpop(key, timeout=0)
            if not result:
                continue
            _, payload = result
            try:
                await ws.send_json(json.loads(payload))
            except Exception:
                await ws.send_json(payload)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/topic/{slug}")
async def topic_ws(
    ws: WebSocket,
    slug: str,
    backlog: int = 50,
    r = Depends(get_rdb),
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
