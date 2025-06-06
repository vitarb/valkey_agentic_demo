from fastapi import FastAPI, WebSocket, Depends
from starlette.websockets import WebSocketDisconnect
from .stream import IStream
from .redis_stream import RedisStream
import os
import redis.asyncio as redis

app = FastAPI()

stream: IStream | None = None
rdb: redis.Redis | None = None

@app.on_event("startup")
async def init_stream():
    """Configure default stream if not provided."""
    global stream
    if stream is None:
        stream = RedisStream(os.getenv("VALKEY_URL", "redis://localhost:6379"))

@app.on_event("startup")
async def init_redis():
    global rdb
    if rdb is None:
        rdb = await redis.from_url(os.getenv("VALKEY_URL", "redis://localhost:6379"), decode_responses=True)

def get_stream() -> IStream:
    assert stream is not None, "Stream not configured"
    return stream

def get_rdb() -> redis.Redis:
    assert rdb is not None, "Redis not configured"
    return rdb

@app.get("/user/{uid}")
async def user(uid: str, r: redis.Redis = Depends(get_rdb)):
    data = await r.json().get(f"user:{uid}")
    if not data:
        return {"interests": []}
    return {"interests": data.get("interests", [])}

@app.websocket("/ws/feed/{uid}")
async def feed_ws(ws: WebSocket, uid: str, s: IStream = Depends(get_stream)):
    await ws.accept()
    try:
        async for item in s.subscribe(f"feed:{uid}"):
            await ws.send_json(item)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/topic/{slug}")
async def topic_ws(ws: WebSocket, slug: str, s: IStream = Depends(get_stream)):
    await ws.accept()
    try:
        async for item in s.subscribe(f"topic:{slug}"):
            await ws.send_json(item)
    except WebSocketDisconnect:
        pass
