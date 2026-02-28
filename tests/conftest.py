"""
Pytest fixtures for load-balance tests
Mock B server requests to avoid sending real traffic
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from unittest.mock import AsyncMock, patch
import redis.asyncio as redis

from app import runtime
from app.config import settings
from app.factory import create_app
from app.rate_limiter import TokenBucketRateLimiter


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def redis_client():
    """Redis client fixture with cleanup"""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    # 清理测试数据（测试前清理，避免上次测试残留）
    await client.flushdb()
    yield client
    # Cleanup: flush test data after test
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def app_client(redis_client):
    """FastAPI test client with mocked B server"""
    app = create_app()
    
    # Override runtime with test redis
    runtime.redis_client = redis_client
    runtime.b_rate_limiter = TokenBucketRateLimiter(settings.b_rate_limit)
    
    # Mock B server HTTP client to avoid real requests
    mock_response = Response(
        status_code=200,
        json={"success": True, "data": {"decrypted": "test_result"}},
    )
    
    with patch("app.worker.runtime.http_b_client") as mock_http:
        mock_http.get = AsyncMock(return_value=mock_response)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    # Cleanup
    if runtime.redis_client:
        await runtime.redis_client.aclose()


@pytest.fixture
def mock_b_server_response():
    """Mock B server response factory"""
    def _mock(success=True, data=None, delay=0):
        async def _get(*args, **kwargs):
            if delay > 0:
                await asyncio.sleep(delay)
            return Response(
                status_code=200,
                json={"success": success, "data": data or {"decrypted": "mock_data"}},
            )
        return _get
    return _mock
