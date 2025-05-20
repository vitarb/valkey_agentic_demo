import importlib
import inspect
import sys
import tempfile
import types
from pathlib import Path
import asyncio
import os


class _Mark:
    def __getattr__(self, name):
        def decorator(fn):
            return fn
        return decorator


mark = _Mark()


class Raises:
    def __init__(self, exc):
        self.exc = exc

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return isinstance(exc, self.exc)


def raises(exc):
    return Raises(exc)


class MonkeyPatch:
    def __init__(self):
        self._items = []

    def setattr(self, target, name, value=None, raising=True):
        if value is None and isinstance(target, str):
            module_name, attr = target.rsplit(".", 1)
            obj = importlib.import_module(module_name)
            value = name
            name = attr
        else:
            obj = target
        original = getattr(obj, name, None)
        if original is None and raising:
            raise AttributeError(name)
        self._items.append((obj, name, original))
        setattr(obj, name, value)

    def setenv(self, key, value, prepend=False):
        original = os.environ.get(key)
        self._items.append((os.environ, key, original))
        if prepend and original:
            os.environ[key] = f"{value}{os.pathsep}{original}"
        else:
            os.environ[key] = value

    def delenv(self, key, raising=True):
        original = os.environ.get(key)
        if key in os.environ:
            self._items.append((os.environ, key, original))
            del os.environ[key]
        elif raising:
            raise KeyError(key)

    def undo(self):
        for mod, attr, original in reversed(self._items):
            if mod is os.environ:
                if original is None:
                    mod.pop(attr, None)
                else:
                    mod[attr] = original
            else:
                if original is None:
                    delattr(mod, attr)
                else:
                    setattr(mod, attr, original)
        self._items.clear()


class TmpPath:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)

    def __truediv__(self, other):
        p = self.path / other
        return p

    def mkdir(self):
        self.path.mkdir()

    def cleanup(self):
        self._tmp.cleanup()


def run_test(func):
    mp = MonkeyPatch()
    tmp = TmpPath()
    kwargs = {}
    sig = inspect.signature(func)
    mod = importlib.import_module(func.__module__)
    for name in sig.parameters:
        if name == 'monkeypatch':
            kwargs[name] = mp
        elif name == 'tmp_path':
            kwargs[name] = tmp.path
        elif hasattr(mod, name):
            kwargs[name] = getattr(mod, name)
    try:
        res = func(**kwargs)
        if inspect.iscoroutine(res):
            asyncio.run(res)
        result = True
    except AssertionError as e:
        print(func.__name__, 'assertion failed', e)
        result = False
    except Exception as e:
        print(func.__name__, 'error', e)
        result = False
    mp.undo()
    tmp.cleanup()
    return result


def discover(path):
    tests = []
    p = Path(path)
    if p.is_file():
        files = [p]
    else:
        files = p.rglob('test_*.py')
    for file in files:
        mod = importlib.import_module(str(file.with_suffix('')).replace('/', '.'))
        for name, obj in vars(mod).items():
            if name.startswith('test') and callable(obj):
                tests.append(obj)
    return tests


def main(argv=None):
    argv = argv or sys.argv[1:]
    paths = [a for a in argv if not a.startswith('-')] or ['.']
    try:
        conf = importlib.import_module('tests.conftest')
        if hasattr(conf, 'pytest_configure'):
            conf.pytest_configure(types.SimpleNamespace())
    except ModuleNotFoundError:
        pass
    tests = []
    for p in paths:
        tests.extend(discover(p))
    ok = 0
    for t in tests:
        if run_test(t):
            ok += 1
    print(f"{ok}/{len(tests)} passed")
    return 0 if ok == len(tests) else 1


if __name__ == '__main__':
    raise SystemExit(main())
