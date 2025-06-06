import pytest
from fastapi.testclient import TestClient
import asyncio

import api_gateway.api_gateway.main as main


class DummyRedis:
    def __init__(self, data=None):
        self.data = data or {}
        self.sent = False
    def json(self):
        outer = self
        class J:
            async def get(self, key):
                return outer.data.get(key)
        return J()
    async def xrevrange(self, *a, count=100):
        return [("1", {"data": "{\"text\": \"hello\"}"})]
    async def xread(self, *a, block=0, count=1):
        if self.sent:
            await asyncio.sleep(0)
            return []
        self.sent = True
        return [(list(a[0].keys())[0], [("2", {"data": "{\"text\": \"world\"}"})])]


@pytest.fixture(autouse=True)
def set_redis(monkeypatch):
    dummy = DummyRedis({"user:0": {"interests": ["news"]}})
    main.rdb = dummy
    yield
    main.rdb = None

@pytest.mark.asyncio
async def test_feed_endpoint():
    client = TestClient(main.app)
    with client.websocket_connect('/ws/feed/0') as ws:
        assert ws.receive_json() == {'text': 'hello'}
        assert ws.receive_json() == {'text': 'world'}

@pytest.mark.asyncio
async def test_topic_endpoint():
    client = TestClient(main.app)
    with client.websocket_connect('/ws/topic/news') as ws:
        assert ws.receive_json() == {'text': 'hello'}
        assert ws.receive_json() == {'text': 'world'}


def test_get_user():
    client = TestClient(main.app)
    resp = client.get('/user/0')
    assert resp.status_code == 200
    assert resp.json() == {'interests': ['news']}


def test_get_user_missing():
    client = TestClient(main.app)
    resp = client.get('/user/99')
    assert resp.status_code == 200
    assert resp.json() == {'interests': []}


def test_websockets_installed():
    """Ensure the websockets library is available for uvicorn."""
    import importlib.util

    assert importlib.util.find_spec("websockets") is not None
