"""Extremely small stub of the :mod:`typer` API used in tests.

This implementation intentionally only covers the very small subset of
functionality required by the test suite.  The goal is to provide a basic CLI
command registry and a simple ``CliRunner`` for invocation without pulling in
external dependencies such as ``click``.
"""

from __future__ import annotations

import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from typing import Any, Callable, Dict, Iterable, List


class Typer:
    """Minimal command container used by the tests."""

    def __init__(self) -> None:
        self._commands: Dict[str, Callable[..., Any]] = {}

    def command(
        self, name: str | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a function as a command."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            cmd_name = name or fn.__name__
            self._commands[cmd_name] = fn
            return fn

        return decorator

    def __call__(self, args: Iterable[str] | None = None) -> Any:
        args = list(args or sys.argv[1:])
        if not args or args[0] in {"-h", "--help"}:
            self._show_help()
            return 0
        cmd_name, *rest = args
        cmd = self._commands.get(cmd_name)
        if cmd is None:
            raise SystemExit(1)
        return cmd(*rest)

    def _show_help(self) -> None:
        print("Commands:")
        for name in sorted(self._commands):
            print(f"  {name}")


class Option:  # noqa: D401 - tiny placeholder used only for type hints
    """Placeholder for ``typer.Option``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - trivial
        pass


@dataclass
class Result:
    """Simple result object mimicking ``click.testing.Result``."""

    exit_code: int
    stdout: str
    exception: Exception | None


class CliRunner:
    """Very small stub of ``typer.testing.CliRunner``."""

    def invoke(self, app: Typer, args: List[str]) -> Result:
        buf = StringIO()
        exc: Exception | None = None
        code = 0
        try:
            with redirect_stdout(buf):
                app(args)
        except SystemExit as e:  # pragma: no cover - not triggered in tests
            code = e.code or 0
            exc = e
        except Exception as e:  # pragma: no cover - not triggered in tests
            code = 1
            exc = e
        return Result(code, buf.getvalue(), exc)


__all__ = ["Typer", "Option", "CliRunner", "Result"]
