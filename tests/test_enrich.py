import sys, importlib
import asyncio
import pytest

# create dummy pipeline to avoid heavy model load
class DummyPipe:
    def __init__(self, out):
        self.out = out
    def __call__(self, inputs, *a, **kw):
        return [self.out for _ in range(len(inputs))]

def load_module(monkeypatch):
    def fake_pipeline(task, *a, **kw):
        if task == "zero-shot-classification":
            return DummyPipe({"labels": ["tech"]})
        return DummyPipe({})
    monkeypatch.setattr("transformers.pipeline", fake_pipeline)
    sys.modules.pop("agents.enrich", None)
    return importlib.import_module("agents.enrich")

@pytest.mark.asyncio
async def test_rconn(monkeypatch):
    mod = load_module(monkeypatch)
    class Stub:
        async def ping(self):
            pass
    async def fake_from_url(url, decode_responses=True):
        return Stub()
    monkeypatch.setattr(mod.redis, "from_url", fake_from_url)
    conn = await mod.rconn()
    assert isinstance(conn, Stub)

@pytest.mark.asyncio
async def test_rconn_retry(monkeypatch):
    mod = load_module(monkeypatch)
    class Stub:
        async def ping(self):
            pass
    calls = {"n": 0}
    async def fake_from_url(url, decode_responses=True):
        calls["n"] += 1
        if calls["n"] == 1:
            raise Exception("fail")
        return Stub()
    monkeypatch.setattr(mod.redis, "from_url", fake_from_url)
    async def noop(*_a, **_k):
        pass
    monkeypatch.setattr(asyncio, "sleep", noop)
    conn = await mod.rconn()
    assert isinstance(conn, Stub)
    assert calls["n"] >= 2

def test_classify(monkeypatch):
    mod = load_module(monkeypatch)
    batch = [{"title": "t", "body": "b"}]
    out = mod.classify(batch)
    assert out[0]["topic"] == "tech"
