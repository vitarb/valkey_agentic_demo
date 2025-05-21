import os
import sys

if os.getenv("USE_MOCK_BOTO3"):
    import boto3_mock as boto3
    sys.modules.setdefault("boto3", boto3)
else:
    try:
        import boto3  # type: ignore
    except ImportError:  # pragma: no cover - defer error until client call
        boto3 = None  # type: ignore
    else:
        if not hasattr(boto3, "reset"):
            def _noop():
                pass
            boto3.reset = _noop  # type: ignore

_state = getattr(boto3, "_state", None)


class LoggingClient:
    """Wrapper around a boto3 client that logs each call."""

    def __init__(self, real_client):
        self._real = real_client

    def __getattr__(self, name):
        try:
            attr = getattr(self._real, name)
        except AttributeError as e:
            print(f"boto3 unknown.{name}()")
            raise e
        if callable(attr):
            def wrapper(*args, **kwargs):
                svc = getattr(getattr(self._real, "meta", None),
                              "service_model", None)
                svc_name = getattr(svc, "service_name", "unknown")
                print(f"boto3 {svc_name}.{name}(")
                if args:
                    print(f"  args={args}")
                if kwargs:
                    print(f"  kwargs={kwargs}")
                print(")")
                return attr(*args, **kwargs)
            return wrapper
        return attr


def client(*a, **k):
    if boto3 is None:
        raise ImportError(
            "boto3 is required when USE_MOCK_BOTO3 is not set. "
            "Install it with 'pip install boto3' or set USE_MOCK_BOTO3=1 to "
            "use the built-in mock."
        )
    print(f"boto3.client(args={a}, kwargs={k})")
    real = boto3.client(*a, **k)
    return LoggingClient(real)

def reset():
    if boto3 is not None:
        return boto3.reset()
