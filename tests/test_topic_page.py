import sys, importlib, types

class DummyQP(dict):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.updates = []
    def update(self, kw):
        self.updates.append(kw)
        for k, v in kw.items():
            self[k] = v

class DummyExpander:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass
    def markdown(self, *a, **k):
        pass

class DummyStreamlit(types.ModuleType):
    def __init__(self, qp, selection=None):
        super().__init__("streamlit")
        self.query_params = qp
        self.selection = selection
        self.rerun_called = False
        self.experimental_rerun = self.rerun
    def set_page_config(self, *a, **k):
        pass
    def markdown(self, *a, **k):
        pass
    def selectbox(self, label, options, index=0, key=None):
        return self.selection if self.selection is not None else options[index]
    def subheader(self, *a, **k):
        pass
    def info(self, *a, **k):
        pass
    def container(self, *a, **k):
        return DummyExpander()
    def rerun(self):
        self.rerun_called = True
        raise RuntimeError("rerun")
    def experimental_get_query_params(self):
        return {k: [v] for k, v in self.query_params.items()}
    def experimental_set_query_params(self, **kw):
        self.query_params.update(kw)
        self.query_params.updates.append(kw)

class DummyRedis:
    def __init__(self):
        self.stream = None
    def ping(self):
        pass
    def xrevrange(self, key, count=None):
        self.stream = key
        return []

def run_page(monkeypatch, qp_mapping, selection=None):
    qp = DummyQP(qp_mapping)
    stmod = DummyStreamlit(qp, selection)
    monkeypatch.setitem(sys.modules, "streamlit", stmod)

    dummy = DummyRedis()
    def fake_from_url(url, decode_responses=True):
        return dummy
    redis_mod = sys.modules.get("redis", types.ModuleType("redis"))
    monkeypatch.setattr(redis_mod, "from_url", fake_from_url, raising=False)
    monkeypatch.setattr(redis_mod, "Redis", DummyRedis, raising=False)
    sys.modules.setdefault("redis", redis_mod)

    sys.modules.pop("agents.pages.Topic", None)
    try:
        importlib.import_module("agents.pages.Topic")
    except RuntimeError:
        pass
    return stmod, dummy.stream

def test_query_passthrough(monkeypatch):
    stmod, stream = run_page(monkeypatch, {"name": "science"})
    assert stream == "topic:science"
    assert stmod.query_params["name"] == "science"


def test_user_select(monkeypatch):
    stmod, stream = run_page(monkeypatch, {"name": "science"}, selection="business")
    assert stmod.rerun_called
    assert stmod.query_params.updates[0] == {"name": "business"}
    stmod2, stream2 = run_page(monkeypatch, stmod.query_params)
    assert stream2 == "topic:business"
