"""
密钥包缓存管理模块
用于去重处理，避免重复解密相同无人机的密钥包

使用Python全局变量实现（适用于单进程部署）
"""
import time
from collections import deque, OrderedDict
from typing import Dict

# 常量定义
MAX_KEYGEN_SUCC_SIZE = 1024  # keygen_succ最大容量
MAX_KEYGEN_BUSY_SIZE = 1024  # keygen_busy最大容量
KEYGEN_BUSY_TIMEOUT = 300    # busy队列超时时间（秒），5分钟

# 全局变量（单进程模式下所有协程共享）
_keygen_succ: deque = deque(maxlen=MAX_KEYGEN_SUCC_SIZE)  # 成功数组，固定大小1024，自动FIFO淘汰
_keygen_busy: OrderedDict[str, float] = OrderedDict()  # 忙碌队列，{drone_id: timestamp}，有序便于FIFO淘汰


async def add_to_keygen_succ(drone_id: str) -> bool:
    """
    添加无人机ID到成功数组（已解密成功）
    
    使用deque实现固定容量的FIFO缓存：
    - maxlen=1024，自动删除最旧的
    
    Args:
        drone_id: 无人机ID（十六进制字符串）
    
    Returns:
        True表示添加成功
    """
    if not drone_id:
        return False
    
    # deque会自动处理超出maxlen的情况，删除最左边（最旧）的元素
    _keygen_succ.append(drone_id)
    print(f"✅ 无人机ID {drone_id} 已加入成功数组 (当前数量: {len(_keygen_succ)})")
    return True


async def is_in_keygen_succ(drone_id: str) -> bool:
    """
    检查无人机ID是否在成功数组中（已解密过）
    
    Args:
        drone_id: 无人机ID
    
    Returns:
        True表示已解密过
    """
    if not drone_id:
        return False
    
    return drone_id in _keygen_succ


async def add_to_keygen_busy(drone_id: str) -> bool:
    """
    添加无人机ID到忙碌队列（正在处理中）
    
    带原子性检查：如果已经在忙碌队列中，返回False
    支持超时清理和大小限制（最大1024）
    
    Args:
        drone_id: 无人机ID
    
    Returns:
        True表示添加成功，False表示已存在
    """
    if not drone_id:
        return False
    
    now = time.time()
    
    # 清理超时条目（超过5分钟的）
    expired_ids = [
        did for did, ts in _keygen_busy.items() 
        if now - ts > KEYGEN_BUSY_TIMEOUT
    ]
    for did in expired_ids:
        del _keygen_busy[did]
        print(f"⏰ 无人机ID {did} 超时已自动从忙碌队列移除")
    
    # 原子性检查：如果已存在，更新时间戳并返回False
    if drone_id in _keygen_busy:
        print(f"⚠️  无人机ID {drone_id} 已在忙碌队列中")
        return False
    
    # 如果队列已满，移除最旧的条目（FIFO）
    while len(_keygen_busy) >= MAX_KEYGEN_BUSY_SIZE:
        oldest_id, oldest_ts = _keygen_busy.popitem(last=False)
        print(f"忙碌队列已满，移除最旧条目: {oldest_id} (等待时间: {now - oldest_ts:.1f}秒)")
    
    _keygen_busy[drone_id] = now
    print(f"无人机ID {drone_id} 已加入忙碌队列 (当前数量: {len(_keygen_busy)})")
    return True


async def remove_from_keygen_busy(drone_id: str) -> bool:
    """
    从忙碌队列移除无人机ID（处理完成）
    
    Args:
        drone_id: 无人机ID
    
    Returns:
        True表示移除成功
    """
    if not drone_id:
        return False
    
    if drone_id in _keygen_busy:
        del _keygen_busy[drone_id]
        print(f"✅ 无人机ID {drone_id} 已从忙碌队列移除")
        return True
    return False


async def is_in_keygen_busy(drone_id: str) -> bool:
    """
    检查无人机ID是否在忙碌队列中（正在处理）
    
    Args:
        drone_id: 无人机ID
    
    Returns:
        True表示正在处理中
    """
    if not drone_id:
        return False
    
    return drone_id in _keygen_busy


async def get_keygen_stats() -> dict:
    """
    获取密钥缓存统计信息
    
    Returns:
        包含成功数组和忙碌队列大小的字典
    """
    return {
        "keygen_succ_count": len(_keygen_succ),
        "keygen_succ_max": MAX_KEYGEN_SUCC_SIZE,
        "keygen_busy_count": len(_keygen_busy),
        "keygen_busy_max": MAX_KEYGEN_BUSY_SIZE,
        "keygen_busy_timeout": KEYGEN_BUSY_TIMEOUT,
    }
