import importlib
import inspect
import sys
import tempfile
import types
from pathlib import Path


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

    def undo(self):
        for mod, attr, original in reversed(self._items):
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
    for name in sig.parameters:
        if name == 'monkeypatch':
            kwargs[name] = mp
        if name == 'tmp_path':
            kwargs[name] = tmp.path
    try:
        func(**kwargs)
        result = True
    except AssertionError:
        result = False
    mp.undo()
    tmp.cleanup()
    return result


def discover(path):
    tests = []
    for file in Path(path).rglob('test_*.py'):
        mod = importlib.import_module(str(file.with_suffix('')).replace('/', '.'))
        for name, obj in vars(mod).items():
            if name.startswith('test') and callable(obj):
                tests.append(obj)
    return tests


def main(argv=None):
    argv = argv or sys.argv[1:]
    paths = [a for a in argv if not a.startswith('-')] or ['.']
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
