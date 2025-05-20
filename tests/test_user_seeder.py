import sys, importlib
import asyncio
import pytest

class DummyJSON:
    def __init__(self, outer):
        self.outer = outer
    async def set(self, key, path, obj):
        self.outer.json_set = (key, path, obj)

class DummyRedis:
    def __init__(self):
        self.json_obj = DummyJSON(self)
        self.zcalls = []
        self.set_latest = None
    def json(self):
        return self.json_obj
    async def zadd(self, key, data):
        self.zcalls.append((key, data))
    async def set(self, key, val):
        self.set_latest = (key, val)
    async def ping(self):
        pass

def load_mod(monkeypatch):
    sys.modules.pop("agents.user_seeder", None)
    return importlib.import_module("agents.user_seeder")

@pytest.mark.asyncio
async def test_rconn(monkeypatch):
    mod = load_mod(monkeypatch)
    async def from_url(url, decode_responses=True):
        return DummyRedis()
    monkeypatch.setattr(mod.redis, "from_url", from_url)
    conn = await mod.rconn()
    assert isinstance(conn, DummyRedis)

@pytest.mark.asyncio
async def test_main_single(monkeypatch):
    dummy = DummyRedis()
    mod = load_mod(monkeypatch)
    async def fake_rconn():
        return dummy
    monkeypatch.setattr(mod, "rconn", fake_rconn)
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)
    monkeypatch.setattr(mod.random, "sample", lambda seq, k: seq[:k])
    monkeypatch.setattr(mod.random, "randint", lambda a,b: 2)
    async def stop(*_a, **_k):
        raise RuntimeError("stop")
    monkeypatch.setattr(asyncio, "sleep", stop)
    with pytest.raises(RuntimeError):
        await mod.main()
    assert dummy.set_latest == ("latest_uid", 0)
    assert dummy.zcalls
