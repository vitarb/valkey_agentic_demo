import sys, types, pathlib, os

# ensure project root is on import path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class DummyMetric:
    def inc(self, *a, **k):
        pass
    def set(self, *a, **k):
        pass
    def labels(self, *a, **k):
        return self
    def time(self):
        class Ctx:
            def __enter__(self):
                pass
            def __exit__(self, exc_type, exc, tb):
                pass
        return Ctx()

dummy_prom = types.SimpleNamespace(
    Counter=lambda *a, **k: DummyMetric(),
    Histogram=lambda *a, **k: DummyMetric(),
    Gauge=lambda *a, **k: DummyMetric(),
    start_http_server=lambda *a, **k: None,
)

dummy_asyncio = types.ModuleType("redis.asyncio")
async def dummy_from_url(*a, **k):
    raise RuntimeError("from_url not patched")
dummy_asyncio.from_url = dummy_from_url

class DummyExc(Exception):
    pass

dummy_exceptions = types.SimpleNamespace(ConnectionError=DummyExc, ResponseError=DummyExc)

dummy_redis = types.ModuleType("redis")
dummy_redis.asyncio = dummy_asyncio
dummy_redis.exceptions = dummy_exceptions

class DummyGraph:
    def add_node(self, *a, **k):
        pass
    def add_edge(self, *a, **k):
        pass
    def set_entry_point(self, *a, **k):
        pass
    def set_finish_point(self, *a, **k):
        pass
    def compile(self):
        class Chain:
            def invoke(self, data):
                return data
        return Chain()

dummy_graph_mod = types.ModuleType("langgraph.graph")
dummy_graph_mod.Graph = DummyGraph

class RunnableLambda:
    def __init__(self, fn):
        self.fn = fn

dummy_runnables = types.ModuleType("langchain_core.runnables")
dummy_runnables.RunnableLambda = RunnableLambda

dummy_transformers = types.ModuleType("transformers")
dummy_transformers.pipeline = lambda *a, **k: None


def pytest_configure(config):
    os.environ.setdefault("USE_MOCK_BOTO3", "1")
    sys.modules.setdefault("redis", dummy_redis)
    sys.modules.setdefault("redis.asyncio", dummy_asyncio)
    sys.modules.setdefault("redis.exceptions", dummy_exceptions)
    sys.modules.setdefault("prometheus_client", dummy_prom)
    sys.modules.setdefault("langgraph.graph", dummy_graph_mod)
    sys.modules.setdefault("langchain_core.runnables", dummy_runnables)
    sys.modules.setdefault("transformers", dummy_transformers)

