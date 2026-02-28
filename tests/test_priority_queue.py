"""
测试优先级队列逻辑

验证任务按照规则排序：
1. 优先级数字越小越优先（priority: 1 > 5 > 10）
2. 相同优先级时，账号创建时间越晚越优先
3. 同一账号的多个请求随机处理
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta

from app.task_service import push_task_to_queue, calculate_queue_score
from app import runtime


@pytest.mark.asyncio
async def test_priority_sorting(redis_client):
    """测试不同优先级用户的任务排序"""
    runtime.redis_client = redis_client
    
    # 模拟三个用户：低优先级、中优先级、高优先级
    users = [
        {"username": "user_low", "priority": 10, "create_time": datetime(2025, 1, 1)},
        {"username": "user_mid", "priority": 5, "create_time": datetime(2025, 6, 1)},
        {"username": "user_high", "priority": 1, "create_time": datetime(2025, 12, 1)},
    ]
    
    # 插入任务（故意乱序）
    print("\n" + "="*60)
    print("测试：不同优先级用户的任务排序")
    print("="*60)
    tasks = []
    for i, user in enumerate([users[1], users[2], users[0]]):  # mid, high, low
        task = {
            "task_id": f"task_{user['username']}_{i}",
            "username": user["username"],
            "priority": user["priority"],
            "create_time": user["create_time"].isoformat(),
            "encrypted_data": "test_data",
        }
        print(f"📥 添加任务: 用户={user['username']}, 优先级={user['priority']}, 创建时间={user['create_time'].date()}")
        await push_task_to_queue(task, user["priority"])
        tasks.append(task)
    print()
    
    # 从队列按顺序取出
    queue_key = "queue:priority"
    result_order = []
    print("📤 队列出队顺序：")
    for i in range(3):
        items = await redis_client.zpopmin(queue_key, 1)
        if items:
            task_data = json.loads(items[0][0])
            result_order.append(task_data["username"])
            print(f"  {i+1}. {task_data['username']} (优先级={task_data['priority']})")
    print("="*60 + "\n")
    
    # 验证顺序：高优先级（1） -> 中优先级（5） -> 低优先级（10）
    assert result_order == ["user_high", "user_mid", "user_low"], \
        f"Expected ['user_high', 'user_mid', 'user_low'], got {result_order}"


@pytest.mark.asyncio
async def test_same_priority_by_create_time(redis_client):
    """测试相同优先级时，按创建时间排序（越晚越优先）"""
    runtime.redis_client = redis_client
    
    priority = 5
    users = [
        {"username": "old_user", "create_time": datetime(2024, 1, 1)},
        {"username": "new_user", "create_time": datetime(2025, 12, 31)},
        {"username": "mid_user", "create_time": datetime(2025, 6, 15)},
    ]
    
    # 乱序插入
    print("\n" + "="*60)
    print("测试：相同优先级时按创建时间排序（越晚越优先）")
    print("="*60)
    for i, user in enumerate([users[2], users[0], users[1]]):
        task = {
            "task_id": f"task_{i}",
            "username": user["username"],
            "priority": priority,
            "create_time": user["create_time"].isoformat(),
            "encrypted_data": "test",
        }
        print(f"📥 添加任务: 用户={user['username']}, 优先级={priority}, 创建时间={user['create_time'].date()}")
        await push_task_to_queue(task, priority)
    print()
    
    # 取出验证
    queue_key = "queue:priority"
    result = []
    print("📤 队列出队顺序：")
    for i in range(3):
        items = await redis_client.zpopmin(queue_key, 1)
        if items:
            username = json.loads(items[0][0])["username"]
            result.append(username)
            create_time = json.loads(items[0][0])["create_time"]
            print(f"  {i+1}. {username} (创建时间={create_time[:10]})")
    print("="*60 + "\n")
    
    # 验证：新用户 -> 中间 -> 老用户
    assert result == ["new_user", "mid_user", "old_user"], \
        f"Expected newer accounts first, got {result}"


@pytest.mark.asyncio
async def test_queue_score_calculation():
    """测试队列分数计算函数"""
    # 高优先级用户
    score_high = calculate_queue_score(1, datetime(2025, 1, 1), "user1")
    # 低优先级用户
    score_low = calculate_queue_score(10, datetime(2025, 1, 1), "user2")
    
    # 优先级1的分数应该小于优先级10（分数越小越优先）
    assert score_high < score_low, "Priority 1 should have lower score than priority 10"
    
    # 相同优先级，创建时间晚的分数更小
    score_old = calculate_queue_score(5, datetime(2024, 1, 1), "old")
    score_new = calculate_queue_score(5, datetime(2025, 12, 31), "new")
    assert score_new < score_old, "Newer account should have lower score"


@pytest.mark.asyncio
async def test_multiple_tasks_same_user(redis_client):
    """测试同一用户的多个任务随机排序（在同优先级内）"""
    runtime.redis_client = redis_client
    
    user = {"username": "test_user", "priority": 5, "create_time": datetime(2025, 6, 1)}
    
    # 同一用户提交10个任务
    for i in range(10):
        task = {
            "task_id": f"task_{i}",
            "username": user["username"],
            "priority": user["priority"],
            "create_time": user["create_time"].isoformat(),
            "encrypted_data": f"data_{i}",
        }
        await push_task_to_queue(task, user["priority"])
    
    # 取出所有任务
    queue_key = "queue:priority"
    task_ids = []
    for _ in range(10):
        items = await redis_client.zpopmin(queue_key, 1)
        if items:
            task_ids.append(json.loads(items[0][0])["task_id"])
    
    # 验证所有任务都存在（不验证顺序，因为是随机的）
    assert len(task_ids) == 10
    assert set(task_ids) == {f"task_{i}" for i in range(10)}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
