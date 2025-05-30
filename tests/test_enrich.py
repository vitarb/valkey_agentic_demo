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
        elif task == "summarization":
            return DummyPipe({"summary_text": "sum"})
        return DummyPipe({})
    monkeypatch.setattr("transformers.pipeline", fake_pipeline)
    if "torch" not in sys.modules:
        import types
        dummy = types.SimpleNamespace()
        dummy.cuda = types.SimpleNamespace(is_available=lambda: False)
        sys.modules["torch"] = dummy
    sys.modules.pop("agents.enrich", None)
    return importlib.import_module("agents.enrich")


@pytest.mark.parametrize("available,expected", [(True, 0), (False, -1)])
def test_device_auto(monkeypatch, available, expected):
    monkeypatch.delenv("ENRICH_USE_CUDA", raising=False)
    import types
    dummy = types.SimpleNamespace()
    dummy.cuda = types.SimpleNamespace(is_available=lambda: available)
    monkeypatch.setitem(sys.modules, "torch", dummy)
    mod = load_module(monkeypatch)
    assert mod.DEVICE == expected

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


@pytest.mark.asyncio
async def test_stream_trim(monkeypatch):
    monkeypatch.setenv("NEWS_RAW_MAXLEN", "5000")
    mod = load_module(monkeypatch)

    class DummyRedis:
        def __init__(self):
            self.streams = {
                mod.SOURCE: [
                    (str(i), {"id": i, "title": "t", "body": "b"})
                    for i in range(6000)
                ]
            }
            self.read_called = False

        async def ping(self):
            pass

        async def xgroup_create(self, *a, **k):
            pass

        async def xreadgroup(self, grp, consumer, streams, count=1, block=0):
            if not self.read_called:
                self.read_called = True
                return [(mod.SOURCE, self.streams[mod.SOURCE][:count])]
            raise RuntimeError("stop")

        async def xack(self, *a, **k):
            pass

        async def xtrim(self, name, maxlen=None, approximate=False):
            if len(self.streams.get(name, [])) > maxlen:
                self.streams[name] = self.streams[name][-maxlen:]

        async def xlen(self, name):
            return len(self.streams.get(name, []))

        def pipeline(self):
            class P:
                def xadd(self, *a, **k):
                    pass

                def xtrim(self, *a, **k):
                    pass

                async def execute(self):
                    pass

            return P()

    dummy = DummyRedis()

    async def fake_rconn():
        return dummy

    monkeypatch.setattr(mod, "rconn", fake_rconn)
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)

    with pytest.raises(RuntimeError):
        await mod.main()

    assert await dummy.xlen(mod.SOURCE) <= mod.NEWS_RAW_MAXLEN


@pytest.mark.asyncio
async def test_backlog_gauge_drop(monkeypatch):
    """BACKLOG gauge should reflect trimmed stream length."""
    monkeypatch.setenv("NEWS_RAW_MAXLEN", "5000")

    recorded = []
    import prometheus_client

    class GaugeRec:
        def __init__(self, *a, **k):
            self.value = 0
        def inc(self, *a, **k):
            pass
        def set(self, v):
            self.value = v
            recorded.append(v)
        def labels(self, *a, **k):
            return self
        def time(self):
            class Ctx:
                def __enter__(self):
                    pass
                def __exit__(self, exc_type, exc, tb):
                    pass
            return Ctx()

    monkeypatch.setattr(prometheus_client, "Gauge", GaugeRec)

    mod = load_module(monkeypatch)

    class DummyRedis:
        def __init__(self):
            self.streams = {
                mod.SOURCE: [
                    (str(i), {"id": i, "title": "t", "body": "b"})
                    for i in range(6000)
                ]
            }
            self.read_called = False

        async def ping(self):
            pass

        async def xgroup_create(self, *a, **k):
            pass

        async def xreadgroup(self, grp, consumer, streams, count=1, block=0):
            if not self.read_called:
                self.read_called = True
                return [(mod.SOURCE, self.streams[mod.SOURCE][:count])]
            raise RuntimeError("stop")

        async def xack(self, *a, **k):
            pass

        async def xtrim(self, name, maxlen=None, approximate=False):
            if len(self.streams.get(name, [])) > maxlen:
                self.streams[name] = self.streams[name][-maxlen:]

        async def xlen(self, name):
            return len(self.streams.get(name, []))

        def pipeline(self):
            class P:
                def xadd(self, *a, **k):
                    pass

                def xtrim(self, *a, **k):
                    pass

                async def execute(self):
                    pass

            return P()

    dummy = DummyRedis()

    async def fake_rconn():
        return dummy

    monkeypatch.setattr(mod, "rconn", fake_rconn)
    monkeypatch.setattr(mod, "start_http_server", lambda *a, **k: None)

    with pytest.raises(RuntimeError):
        await mod.main()

    assert recorded[-1] == await dummy.xlen(mod.SOURCE)
    assert recorded[-1] < 6000
