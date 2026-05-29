import pytest
import respx
import fakeredis.aioredis

@pytest.fixture
def mock_hub_api():
    with respx.mock(base_url="https://hub.xovis.com") as respx_mock:
        yield respx_mock

@pytest.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.close()
