import asyncio
import pytest
from typing import Any, AsyncIterator

class DummyStream:
    def __init__(self, items):
        self.items = items

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        for item in self.items:
            await asyncio.sleep(0)
            yield item

@pytest.fixture
def dummy_stream():
    return DummyStream([
        {"text": "hello"},
        {"text": "world"},
    ])
