import pytest
from fastapi.testclient import TestClient

import api_gateway.api_gateway.main as main

@pytest.fixture(autouse=True)
def set_stream(dummy_stream):
    main.stream = dummy_stream
    yield
    main.stream = None

@pytest.mark.asyncio
async def test_feed_endpoint(dummy_stream):
    client = TestClient(main.app)
    with client.websocket_connect('/ws/feed/0') as ws:
        assert ws.receive_json() == {'text': 'hello'}
        assert ws.receive_json() == {'text': 'world'}

@pytest.mark.asyncio
async def test_topic_endpoint(dummy_stream):
    client = TestClient(main.app)
    with client.websocket_connect('/ws/topic/news') as ws:
        assert ws.receive_json() == {'text': 'hello'}
        assert ws.receive_json() == {'text': 'world'}
