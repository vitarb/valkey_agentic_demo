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


class TrimRedis(DummyRedis):
    def __init__(self):
        super().__init__()
        self.entries = [(str(i), {"data": "{}"}) for i in range(200)]
        self.read = False
    async def xgroup_create(self, *a, **k):
        pass
    async def xreadgroup(self, grp, consumer, streams, count=32, block=50):
        if self.read:
            return []
        self.read = True
        key = list(streams.keys())[0]
        return [(key, self.entries.copy())]
    async def zrange(self, *a):
        return []
    async def evalsha(self, sha, numkeys, *args):
        max_len = int(args[-1])
        if len(self.entries) > max_len:
            self.entries = self.entries[-max_len:]
        return 0
    async def xack(self, *a):
        pass
    async def xlen(self, stream):
        return len(self.entries)


@pytest.mark.asyncio
async def test_stream_trim(monkeypatch):
    monkeypatch.setenv("MAX_LEN", "100")
    mod = load_module(monkeypatch)
    dummy = TrimRedis()
    async def fake_rconn():
        return dummy
    monkeypatch.setattr(mod, "rconn", fake_rconn)
    monkeypatch.setattr(mod, "load_sha", lambda *_: "sha")
    monkeypatch.setattr(mod, "TOPICS", ["t"])
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)
    async def stop(*_a, **_k):
        raise RuntimeError("stop")
    monkeypatch.setattr(asyncio, "sleep", stop)
    with pytest.raises(RuntimeError):
        await mod.main()
    assert len(dummy.entries) < 200
