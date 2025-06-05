from typing import AsyncIterator, Protocol, Any

class IStream(Protocol):
    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        ...
