from fastapi import FastAPI, WebSocket, Depends
from .stream import IStream
from .redis_stream import RedisStream
import os

app = FastAPI()

stream: IStream | None = None

@app.on_event("startup")
async def init_stream():
    """Configure default stream if not provided."""
    global stream
    if stream is None:
        stream = RedisStream(os.getenv("VALKEY_URL", "redis://localhost:6379"))

def get_stream() -> IStream:
    assert stream is not None, "Stream not configured"
    return stream

@app.websocket("/ws/feed/{uid}")
async def feed_ws(ws: WebSocket, uid: str, s: IStream = Depends(get_stream)):
    await ws.accept()
    async for item in s.subscribe(f"feed:{uid}"):
        await ws.send_json(item)

@app.websocket("/ws/topic/{slug}")
async def topic_ws(ws: WebSocket, slug: str, s: IStream = Depends(get_stream)):
    await ws.accept()
    async for item in s.subscribe(f"topic:{slug}"):
        await ws.send_json(item)
