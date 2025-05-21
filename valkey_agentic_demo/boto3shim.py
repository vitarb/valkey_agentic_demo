import os
import sys

if os.getenv("USE_MOCK_BOTO3"):
    import boto3_mock as boto3
    sys.modules.setdefault("boto3", boto3)
else:
    try:
        import boto3  # type: ignore
    except ImportError:  # pragma: no cover - fallback when boto3 not installed
        import boto3_mock as boto3  # noqa: F401
    else:
        if not hasattr(boto3, "reset"):
            def _noop():
                pass
            boto3.reset = _noop  # type: ignore

_state = getattr(boto3, "_state", None)

def client(*a, **k):
    return boto3.client(*a, **k)

def reset():
    return boto3.reset()
