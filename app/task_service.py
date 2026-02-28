import json
import random
import time
from datetime import datetime

from sqlalchemy import update, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SysUser
from .config import settings
from . import runtime


def calculate_queue_score(priority: int, update_time: datetime, username: str) -> float:
    """
    计算队列优先级分数，分数越小优先级越高
    
    规则：
    1. 优先按priority排序（数字越小优先级越高）
    2. priority相同时，按账号更新时间排序（时间越新优先级越高）
    
    Args:
        priority: 用户优先级（1-999）
        update_time: 账号更新时间
        username: 用户名
    
    Returns:
        float: 队列分数，越小优先级越高
    """
    # priority占主要权重（乘以1e15确保优先级是最重要的因素）
    priority_score = priority * 1e15
    
    # 账号更新时间：时间越新（时间戳越大），分数越小（优先级越高）
    # 使用负数确保时间越新分数越小
    if update_time:
        update_time_score = -update_time.timestamp() * 1e6
    else:
        # 如果没有更新时间，使用一个默认值（低优先级）
        update_time_score = 0
    
    # 最终分数（去掉随机数，确保排序完全确定性）
    return priority_score + update_time_score


async def push_task_to_queue(task: dict, priority: int):
    """
    将任务推入优先级队列
    
    使用Redis有序集合(sorted set)实现复杂的排队规则：
    1. 优先级越小越高
    2. 相同优先级时，账号创建时间越晚越高
    3. 同一账号的多个请求随机处理
    """
    if not runtime.redis_client:
        raise RuntimeError("Redis not initialized")
    
    # 检查队列长度，超过限制则拒绝
    queue_key = "queue:priority"
    queue_size = await runtime.redis_client.zcard(queue_key)
    if queue_size >= settings.max_queue_size:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exceeds the system's maximum length"
        )
    
    # 解析账号更新时间
    update_time_str = task.get('update_time', '')
    try:
        if update_time_str:
            update_time = datetime.fromisoformat(update_time_str.replace('Z', '+00:00'))
        else:
            update_time = None
    except:
        update_time = None
    
    # 计算队列分数
    score = calculate_queue_score(
        priority=priority,
        update_time=update_time,
        username=task.get('username', '')
    )
    
    # 使用有序集合存储任务
    queue_member = json.dumps(task)
    await runtime.redis_client.zadd(
        queue_key,
        {queue_member: score}
    )
    
    # 设置任务状态，TTL = queue_wait_timeout，超时自动过期
    await runtime.redis_client.set(
        f"task:{task['task_id']}",
        json.dumps({"status": "queued"}),
        ex=settings.queue_wait_timeout
    )


    # 用户配额相关逻辑已移除，如需实现请在SysUser表扩展字段后补充
