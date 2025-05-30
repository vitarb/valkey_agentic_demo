import sys, importlib
import asyncio
import pytest

class DummyRedis:
    def __init__(self):
        self.loaded = None
        self.lists = {}
        self.users = ["0"]
    async def script_load(self, lua):
        self.loaded = lua
        return "sha123"
    async def ping(self):
        pass
    async def evalsha(self, sha, numkeys, *args):
        _id, topic, payload_json, max_len = args
        max_len = int(max_len)
        for u in self.users:
            key = f"feed:{u}"
            self.lists.setdefault(key, [])
            self.lists[key].insert(0, payload_json)
            self.lists[key] = self.lists[key][:max_len]
        return len(self.users)
    async def llen(self, key):
        return len(self.lists.get(key, []))

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

@pytest.mark.asyncio
async def test_feed_ltrim(monkeypatch):
    mod = load_module(monkeypatch)
    dummy = DummyRedis()
    sha = await mod.load_sha(dummy)

    for i in range(150):
        await dummy.evalsha(sha, 0, str(i), "tech", "{}", mod.TOPIC_MAX_LEN)

    ln = await dummy.llen("feed:0")
    assert ln <= mod.TOPIC_MAX_LEN

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
    monkeypatch.setenv("TOPIC_MAXLEN", "100")
    mod = load_module(monkeypatch)
    dummy = TrimRedis()
    async def fake_rconn():
        return dummy
    monkeypatch.setattr(mod, "rconn", fake_rconn)
    async def fake_load_sha(*_):
        return "sha"
    monkeypatch.setattr(mod, "load_sha", fake_load_sha)
    monkeypatch.setattr(mod, "TOPICS", ["t"])
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)
    async def stop(*_a, **_k):
        raise RuntimeError("stop")
    monkeypatch.setattr(asyncio, "sleep", stop)
    with pytest.raises(RuntimeError):
        await mod.main()
    assert len(dummy.entries) < 200

