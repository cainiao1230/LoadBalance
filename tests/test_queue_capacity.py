"""
测试队列容量限制和其他边界条件

验证：
1. 队列满时（200个任务）拒绝新任务并返回503
2. TTL超时后任务自动清理
3. 并发入队的正确性
"""
import pytest
import asyncio
import json
from fastapi import HTTPException

from app.task_service import push_task_to_queue
from app import runtime
from app.config import settings


@pytest.mark.asyncio
async def test_queue_full_rejection(redis_client):
    """测试队列满时拒绝新任务"""
    runtime.redis_client = redis_client
    
    # 清空队列（避免之前测试残留）
    await redis_client.delete("queue:priority")
    await asyncio.sleep(0.1)
    
    # 填满队列到最大容量
    for i in range(settings.max_queue_size):
        # 确保每个任务都唯一（避免JSON重复被zadd覆盖）
        task = {
            "task_id": f"task_{i:05d}",
            "username": f"user_{i % 10}",
            "priority": (i % 3) + 1,
            "create_time": f"2025-01-{(i // 1440) + 1:02d}T{(i // 60) % 24:02d}:{i % 60:02d}:00",  # 唯一时间戳
            "encrypted_data": f"test_data_{i}",
        }
        try:
            await push_task_to_queue(task, task["priority"])
        except Exception as e:
            # 如果队列满了会抛出异常，这是预期的
            if i < settings.max_queue_size - 1:
                # 如果还没到最大值就抛异常，说明有问题
                raise
            break
    
    # 验证队列已满
    queue_size = await redis_client.zcard("queue:priority")
    assert queue_size == settings.max_queue_size, f"Expected queue to be full ({settings.max_queue_size}), got {queue_size}"
    
    # 现在队列满了，尝试再添加一个任务，应该抛出503异常
    with pytest.raises(HTTPException) as exc_info:
        overflow_task = {
            "task_id": "overflow",
            "username": "overflow_user",
            "priority": 1,
            "create_time": "2025-01-01T00:00:00",
            "encrypted_data": "test",
        }
        await push_task_to_queue(overflow_task, 1)
    
    assert exc_info.value.status_code == 503
    assert "full" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_task_ttl_expiration(redis_client):
    """测试任务TTL超时自动清理"""
    runtime.redis_client = redis_client
    
    # 创建一个任务
    task = {
        "task_id": "ttl_test",
        "username": "test_user",
        "priority": 5,
        "create_time": "2025-01-01T00:00:00",
        "encrypted_data": "test",
    }
    await push_task_to_queue(task, 5)
    
    # 等待一下确保Redis操作完成
    await asyncio.sleep(0.1)
    
    # 验证任务状态key存在且有TTL
    task_key = f"task:{task['task_id']}"
    exists = await redis_client.exists(task_key)
    
    # 调试：检查所有keys
    if exists != 1:
        all_keys = await redis_client.keys("*")
        print(f"DEBUG: Task key '{task_key}' not found. All keys: {all_keys}")
    
    assert exists == 1, f"Task key '{task_key}' should exist but doesn't"
    
    ttl = await redis_client.ttl(task_key)
    assert ttl > 0 and ttl <= settings.queue_wait_timeout
    
    # 设置一个很短的TTL测试（覆盖原TTL）
    await redis_client.expire(task_key, 1)
    
    # 等待过期
    await asyncio.sleep(1.5)
    
    # 主动访问key触发Redis过期检查（惰性删除机制）
    ttl_after = await redis_client.ttl(task_key)
    
    # 验证任务状态key已经过期（ttl返回-2表示key不存在）
    assert ttl_after == -2, f"Task key should be expired (TTL=-2), but TTL={ttl_after}"
    
    # 注意：队列中的成员不会自动过期（Redis sorted set特性）
    # 这由Worker在处理时检查任务状态来判断是否已超时


@pytest.mark.asyncio
async def test_concurrent_queue_operations(redis_client):
    """测试并发入队的正确性"""
    runtime.redis_client = redis_client
    
    async def add_tasks(user_id, count):
        """并发添加任务"""
        for i in range(count):
            task = {
                "task_id": f"user{user_id}_task{i}",
                "username": f"user_{user_id}",
                "priority": user_id % 5 + 1,
                "create_time": f"2025-01-01T00:{user_id:02d}:{i:02d}",  # 不同时间
                "encrypted_data": f"test_data_u{user_id}_t{i}",  # 不同数据
            }
            await push_task_to_queue(task, task["priority"])
    
    # 10个用户并发，每人添加5个任务
    tasks = [add_tasks(i, 5) for i in range(10)]
    await asyncio.gather(*tasks)
    
    # 验证队列大小正确
    queue_size = await redis_client.zcard("queue:priority")
    assert queue_size == 50, f"Expected 50 tasks, got {queue_size}"
    
    # 验证所有任务都在队列中
    all_items = await redis_client.zrange("queue:priority", 0, -1)
    task_ids = {json.loads(item)["task_id"] for item in all_items}
    
    expected_ids = {f"user{i}_task{j}" for i in range(10) for j in range(5)}
    assert task_ids == expected_ids


@pytest.mark.asyncio
async def test_queue_priority_consistency(redis_client):
    """测试队列在压力下的优先级一致性"""
    runtime.redis_client = redis_client
    
    # 添加100个混合优先级的任务
    for i in range(100):
        task = {
            "task_id": f"task_{i}",
            "username": f"user_{i % 20}",
            "priority": (i % 10) + 1,  # 优先级1-10
            "create_time": f"2025-{(i % 12) + 1:02d}-01T00:00:00",
            "encrypted_data": "test",
        }
        await push_task_to_queue(task, task["priority"])
    
    # 取出前10个任务
    queue_key = "queue:priority"
    top_10_priorities = []
    for _ in range(10):
        result = await redis_client.zpopmin(queue_key, 1)
        if result:
            task_data = json.loads(result[0][0])
            top_10_priorities.append(task_data["priority"])
    
    # 验证前10个任务都是高优先级（1或2）
    assert all(p <= 3 for p in top_10_priorities), \
        f"Top 10 should be high priority, got {top_10_priorities}"
    
    # 验证优先级是递增的（允许同优先级）
    for i in range(1, len(top_10_priorities)):
        assert top_10_priorities[i] >= top_10_priorities[i-1], \
            f"Priorities not sorted: {top_10_priorities}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
