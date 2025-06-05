from fastapi import FastAPI, WebSocket, Depends
from .stream import IStream

app = FastAPI()

stream: IStream | None = None

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
