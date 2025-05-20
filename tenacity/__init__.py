def retry(fn=None, *dargs, **dkwargs):
    """Very small stub allowing ``@retry`` or ``@retry()`` usage."""

    def decorator(func):
        def wrapper(*args, **kw):
            try:
                return func(*args, **kw)
            except Exception:
                return func(*args, **kw)

        return wrapper

    if callable(fn):
        return decorator(fn)
    return decorator
