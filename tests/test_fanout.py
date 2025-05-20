import sys, importlib
import asyncio
import pytest

class DummyRedis:
    def __init__(self):
        self.loaded = None
    async def script_load(self, lua):
        self.loaded = lua
        return "sha123"
    async def ping(self):
        pass

async def fake_from_url(url, decode_responses=True):
    return DummyRedis()

def load_module(monkeypatch):
    sys.modules.pop("agents.fanout", None)
    return importlib.import_module("agents.fanout")

@pytest.mark.asyncio
async def test_rconn(monkeypatch):
    mod = load_module(monkeypatch)
    monkeypatch.setattr(mod.redis, "from_url", fake_from_url)
    conn = await mod.rconn()
    assert isinstance(conn, DummyRedis)

@pytest.mark.asyncio
async def test_load_sha(monkeypatch, tmp_path):
    mod = load_module(monkeypatch)
    script = tmp_path/"fanout.lua"
    script.write_text("return 1")
    monkeypatch.setattr(mod, "open", lambda *_: open(script, 'r'))
    redis_inst = DummyRedis()
    sha = await mod.load_sha(redis_inst)
    assert sha == "sha123"
    assert redis_inst.loaded == "return 1"
