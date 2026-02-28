"""
测试速率限制逻辑

验证Token Bucket算法的正确性，不依赖外部组件
"""
import pytest
import asyncio
import time

from app.rate_limiter import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """测试速率限制器基本功能"""
    rate_limit = 10  # 10 req/s
    limiter = TokenBucketRateLimiter(rate_limit)
    
    # 获取10个token（应该立即成功，因为初始有10个token）
    start = time.time()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.time() - start
    
    # 应该在很短时间内完成（< 0.2秒）
    assert elapsed < 0.2, f"First 10 requests took {elapsed}s, should be instant"
    
    # 再获取5个token（应该需要等待约0.5秒，因为每秒生成10个）
    start = time.time()
    for _ in range(5):
        await limiter.acquire()
    elapsed = time.time() - start
    
    # 应该等待约0.5秒（允许±0.2秒误差）
    assert 0.3 < elapsed < 0.7, f"Next 5 requests took {elapsed}s, expected ~0.5s"


@pytest.mark.asyncio
async def test_rate_limiter_refill():
    """测试Token自动补充"""
    rate_limit = 20  # 20 req/s
    limiter = TokenBucketRateLimiter(rate_limit)
    
    # 快速消耗20个token
    for _ in range(20):
        await limiter.acquire()
    
    # 等待0.5秒，应该补充10个token
    await asyncio.sleep(0.5)
    
    # 应该能立即获取10个token
    start = time.time()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.time() - start
    
    assert elapsed < 0.2, f"Should have 10 tokens after 0.5s refill, but took {elapsed}s"


@pytest.mark.asyncio
async def test_concurrent_rate_limit():
    """测试并发请求的速率控制"""
    rate_limit = 50  # 50 req/s（生产环境配置）
    limiter = TokenBucketRateLimiter(rate_limit)
    
    async def acquire_token():
        await limiter.acquire()
        return time.time()
    
    # 并发发起100个请求
    start = time.time()
    tasks = [acquire_token() for _ in range(100)]
    timestamps = await asyncio.gather(*tasks)
    total_time = time.time() - start
    
    # 前50个请求立即完成（初始bucket满），后50个请求需要1秒
    # 总时间约1秒（允许±0.4秒误差，考虑系统调度）
    assert 0.6 < total_time < 1.5, f"100 requests at 50 req/s took {total_time}s, expected ~1s"
    
    # 验证速率：后50个请求的平均速率应该接近50 req/s
    # 取后50个请求计算速率
    if len(timestamps) >= 50:
        last_50_duration = timestamps[-1] - timestamps[49]
        if last_50_duration > 0:
            last_50_rate = 50 / last_50_duration
            assert 40 < last_50_rate < 65, f"Last 50 requests rate {last_50_rate:.1f} req/s, expected ~50 req/s"


@pytest.mark.asyncio
async def test_rate_limiter_state():
    """测试速率限制器状态管理"""
    limiter = TokenBucketRateLimiter(10)
    
    # 初始应该有10个token
    assert limiter.tokens > 0
    
    # 消耗5个token
    for _ in range(5):
        await limiter.acquire()
    
    # 应该剩余约5个token（考虑时间流逝可能补充）
    assert 4 <= limiter.tokens <= 10
