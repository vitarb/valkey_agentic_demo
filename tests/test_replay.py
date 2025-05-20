import sys, importlib
import asyncio
import pytest

class DummyRedis:
    def __init__(self):
        self.adds = []
    async def ping(self):
        pass
    async def xadd(self, name, data):
        self.adds.append((name, data))

def load_mod(monkeypatch):
    sys.modules.pop("agents.replay", None)
    return importlib.import_module("agents.replay")

@pytest.mark.asyncio
async def test_redis_ready(monkeypatch):
    mod = load_mod(monkeypatch)
    async def fake_from_url(url, decode_responses=True):
        return DummyRedis()
    monkeypatch.setattr(mod.redis, "from_url", fake_from_url)
    conn = await mod.redis_ready()
    assert isinstance(conn, DummyRedis)

@pytest.mark.asyncio
async def test_main(monkeypatch, tmp_path):
    csvfile = tmp_path / "sample.csv"
    csvfile.write_text("id,title,text\n1,a,b\n2,c,d\n")
    mod = load_mod(monkeypatch)
    monkeypatch.setenv("REPLAY_FILE", str(csvfile))
    dummy = DummyRedis()
    async def rr():
        return dummy
    monkeypatch.setattr(mod, "redis_ready", rr)
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)
    async def sleep(*_a, **_k):
        pass
    monkeypatch.setattr(asyncio, "sleep", sleep)
    await mod.main()
    assert len(dummy.adds) == 2
