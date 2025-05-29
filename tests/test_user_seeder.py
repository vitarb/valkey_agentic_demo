import sys, importlib
import asyncio
import pytest

class DummyJSON:
    def __init__(self, outer):
        self.outer = outer
    async def set(self, key, path, obj):
        self.outer.json_set = (key, path, obj)
        self.outer.docs[key] = obj
    async def get(self, key, path):
        doc = self.outer.docs.get(key)
        if doc is None:
            return None
        if path == "$.interests":
            return [doc.get("interests", [])]
        return doc

class DummyPipeline:
    def __init__(self, outer):
        self.outer = outer
        self.ops = []
    def json(self):
        pipeline = self
        class J:
            def set(self, key, path, obj):
                pipeline.ops.append(("json.set", key, path, obj))
        return J()
    def zadd(self, key, data):
        self.ops.append(("zadd", key, data))
    def set(self, key, val):
        self.ops.append(("set", key, val))
    async def execute(self):
        for op in self.ops:
            if op[0] == "json.set":
                await self.outer.json().set(op[1], op[2], op[3])
            elif op[0] == "zadd":
                await self.outer.zadd(op[1], op[2])
            elif op[0] == "set":
                await self.outer.set(op[1], op[2])
        self.ops = []

class DummyRedis:
    def __init__(self):
        self.json_obj = DummyJSON(self)
        self.zcalls = []
        self.set_latest = None
        self.docs = {}
        self.zsets = {}
    def json(self):
        return self.json_obj
    def pipeline(self, transaction=True):
        return DummyPipeline(self)
    async def zadd(self, key, data):
        self.zcalls.append((key, data))
        self.zsets.setdefault(key, {}).update(data)
    async def set(self, key, val):
        self.set_latest = (key, val)
    async def exists(self, key):
        return int(key in self.docs)
    async def get(self, key):
        return None
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

def test_idempotent(monkeypatch):
    async def run():
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

        first_interests = dummy.docs["user:0"]["interests"]
        first_sets = {k: set(v.keys()) for k, v in dummy.zsets.items()}

        with pytest.raises(RuntimeError):
            await mod.main()

        assert dummy.docs["user:0"]["interests"] == first_interests
        second_sets = {k: set(v.keys()) for k, v in dummy.zsets.items()}
        assert second_sets == first_sets
        for t in mod.TOPICS:
            key = f"user:topic:{t}"
            if t in first_interests:
                assert 0 in dummy.zsets.get(key, {})
            else:
                assert 0 not in dummy.zsets.get(key, {})

    asyncio.run(run())
