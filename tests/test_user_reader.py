import sys, importlib
import asyncio
import pytest

class DummyRedis:
    def __init__(self):
        self.popped = 0
    async def ping(self):
        pass
    async def get(self, key):
        return "5"
    async def brpop(self, key, timeout=1):
        self.popped += 1


def load_mod(monkeypatch):
    sys.modules.pop("agents.user_reader", None)
    return importlib.import_module("agents.user_reader")

@pytest.mark.asyncio
async def test_rconn(monkeypatch):
    mod = load_mod(monkeypatch)
    async def fake_from_url(url, decode_responses=True):
        return DummyRedis()
    monkeypatch.setattr(mod.redis, "from_url", fake_from_url)
    conn = await mod.rconn()
    assert isinstance(conn, DummyRedis)

@pytest.mark.asyncio
async def test_main_single_loop(monkeypatch):
    dummy = DummyRedis()
    mod = load_mod(monkeypatch)
    async def fake_rconn():
        return dummy
    monkeypatch.setattr(mod, "rconn", fake_rconn)
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)
    async def stop(*_a, **_k):
        raise RuntimeError("stop")
    monkeypatch.setattr(asyncio, "sleep", stop)
    with pytest.raises(RuntimeError):
        await mod.main()
    assert dummy.popped == 1
