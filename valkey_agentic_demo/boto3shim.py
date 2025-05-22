import boto3


def client(*args, **kwargs):
    """Return a regular boto3 client."""
    return boto3.client(*args, **kwargs)


def reset() -> None:  # pragma: no cover - kept for API compatibility
    """No-op reset hook maintained for backward compatibility."""
    pass
