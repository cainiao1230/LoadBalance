"""
负载均衡模块
管理多服务器密钥分发和路由

功能：
1. DroneKeyInfo 数据类：存储无人机密钥信息（server_idx, hash_code, sn）
2. 服务器状态管理：繁忙状态（36秒超时）、独立Token管理（23小时刷新）
3. 密钥路由：根据hash_code查找密钥所在服务器
4. 负载均衡：选择空闲服务器处理新密钥包
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict
from enum import Enum
from datetime import datetime, timedelta


# ==================== 常量定义 ====================
MAX_KEY_CACHE_SIZE = 4096           # 密钥缓存最大容量
MAX_BUSY_QUEUE_SIZE = 1024          # 忙碌队列最大容量
SERVER_BUSY_TIMEOUT = 36            # 服务器繁忙超时时间（秒）
KEY_BUSY_TIMEOUT = 36              # 密钥处理超时时间（秒），5分钟
TOKEN_REFRESH_HOURS = 23            # Token刷新间隔（小时）


class ServerStatus(Enum):
    """服务器状态枚举"""
    IDLE = "idle"           # 空闲
    BUSY = "busy"           # 繁忙（正在处理密钥包）


@dataclass
class DroneKeyInfo:
    """
    无人机密钥信息
    
    Attributes:
        server_idx: 密钥所在服务器索引
        hash_code: 无人机临时ID（uint32，4字节，对应hex 8字符）
        sn: 无人机全球唯一序列号（17字符）
        timestamp: 记录时间戳
    """
    server_idx: int                    # 记录密钥在哪个服务器
    hash_code: str                     # 无人机临时ID（hex字符串，8字符）
    sn: str = ""                       # 无人机全球唯一序列号（17字符）
    timestamp: float = field(default_factory=time.time)  # 记录时间
    
    def __post_init__(self):
        """验证字段"""
        if len(self.hash_code) != 8:
            raise ValueError(f"hash_code must be 8 hex chars (4 bytes), got {len(self.hash_code)}")
        # sn 可以为空（密钥包刚加入处理时还没有sn）
        if self.sn and len(self.sn) > 17:
            self.sn = self.sn[:17]  # 截断到17字符


@dataclass
class ServerInfo:
    """
    服务器信息（包含独立的Token管理）
    
    Attributes:
        idx: 服务器索引
        url: 服务器URL
        username: 登录账号
        password: 登录密码
        status: 服务器状态
        busy_until: 繁忙状态结束时间戳（None表示空闲）
        token: 当前有效的JWT Token
        token_fetch_time: Token获取时间
    """
    idx: int
    url: str
    username: str = ""
    password: str = ""
    status: ServerStatus = ServerStatus.IDLE
    busy_until: Optional[float] = None
    # Token管理
    token: Optional[str] = None
    token_fetch_time: Optional[datetime] = None
    
    def is_busy(self) -> bool:
        """检查服务器是否繁忙"""
        if self.status == ServerStatus.IDLE:
            return False
        # 检查繁忙状态是否超时
        if self.busy_until and time.time() > self.busy_until:
            self.status = ServerStatus.IDLE
            self.busy_until = None
            return False
        return True
    
    def set_busy(self, timeout: int = SERVER_BUSY_TIMEOUT):
        """设置服务器为繁忙状态"""
        self.status = ServerStatus.BUSY
        self.busy_until = time.time() + timeout
        
    def set_idle(self):
        """设置服务器为空闲状态"""
        self.status = ServerStatus.IDLE
        self.busy_until = None
    
    def need_refresh_token(self) -> bool:
        """检查是否需要刷新Token"""
        if self.token is None or self.token_fetch_time is None:
            return True
        now = datetime.utcnow()
        return (now - self.token_fetch_time) > timedelta(hours=TOKEN_REFRESH_HOURS)
    
    def update_token(self, token: str):
        """更新Token"""
        self.token = token
        self.token_fetch_time = datetime.utcnow()
        print(f"服务器 {self.idx} ({self.url}) Token已更新")
    
    def invalidate_token(self):
        """使Token失效（强制下次刷新）"""
        self.token = None
        self.token_fetch_time = None
        print(f" 服务器 {self.idx} ({self.url}) Token已失效，下次请求时刷新")


# ==================== 全局状态 ====================
# 服务器列表（在初始化时配置）
_servers: List[ServerInfo] = []

# 密钥缓存：{hash_code: DroneKeyInfo}，存储已成功解密的密钥
# 使用OrderedDict实现LRU淘汰
_key_cache: OrderedDict[str, DroneKeyInfo] = OrderedDict()#表示这个有序字典的键（key）是字符串类型，值（value）是 DroneKeyInfo 类型的对象。每个键对应一个无人机密钥信息的数据对象，并且插入顺序会被保留。

# 用于防止重复处理
_processing_keys: OrderedDict[str, Tuple[int, float]] = OrderedDict()

# 轮询负载均衡：记录上一次分配的服务器索引
_last_dispatch_server_idx: int = -1


# ==================== 服务器管理 ====================
def init_servers(server_configs: list) -> None:
    """
    初始化服务器列表
    
    Args:
        server_configs: 服务器配置列表，每项包含 url, username, password
    """
    global _servers
    _servers = [
        ServerInfo(
            idx=i, 
            url=cfg.url,
            username=cfg.username,
            password=cfg.password
        ) 
        for i, cfg in enumerate(server_configs)
    ]
    print(f"负载均衡初始化完成，共 {len(_servers)} 台服务器")
    for s in _servers:
        print(f"   - 服务器 {s.idx}: {s.url} (账号: {s.username})")


def get_server_count() -> int:
    """获取服务器数量"""
    return len(_servers)


def get_server(idx: int) -> Optional[ServerInfo]:
    """获取指定索引的服务器"""
    if 0 <= idx < len(_servers):
        return _servers[idx]
    return None


def get_all_servers() -> List[ServerInfo]:
    """获取所有服务器"""
    return _servers.copy()


def get_idle_server() -> Optional[ServerInfo]:
    """
    获取一台空闲服务器（负载均衡策略）
    
    策略：轮询（Round-Robin）- 从上一次分配的服务器索引+1开始查找空闲服务器
    这样可以确保新密钥包均匀分配到各个服务器，避免总是优先使用索引小的服务器
    
    Returns:
        空闲服务器，如果都繁忙则返回None
    """
    global _last_dispatch_server_idx
    
    if not _servers:
        return None
    
    server_count = len(_servers)
    
    # 从上一次分配的索引+1开始轮询
    start_idx = (_last_dispatch_server_idx + 1) % server_count
    
    # 遍历所有服务器，找到第一个空闲的
    for i in range(server_count):
        check_idx = (start_idx + i) % server_count
        server = _servers[check_idx]
        if not server.is_busy():
            # 找到空闲服务器，记录上次索引用于打印
            previous_idx = _last_dispatch_server_idx if _last_dispatch_server_idx >= 0 else None
            # 更新轮询索引
            _last_dispatch_server_idx = check_idx
            # 打印轮询信息
            if previous_idx is not None:
                print(f"轮询分配服务器: {check_idx} (上次: {previous_idx})")
            else:
                print(f" 轮询分配服务器: {check_idx} (首次分配)")
            return server
    
    # 所有服务器都繁忙
    return None


def set_server_busy(server_idx: int) -> bool:
    """
    设置服务器为繁忙状态
    
    Args:
        server_idx: 服务器索引
    
    Returns:
        是否设置成功
    """
    server = get_server(server_idx)
    if server:
        server.set_busy()
        print(f" 服务器 {server_idx} 设置为繁忙状态")
        return True
    return False


# ==================== 密钥缓存管理 ====================
async def add_key_to_cache(hash_code: str, server_idx: int, sn: str = "") -> bool:
    """
    添加密钥到缓存（密钥包解密成功后调用）
    
    Args:
        hash_code: 无人机临时ID（hex字符串，8字符）
        server_idx: 密钥所在服务器索引
        sn: 无人机全球唯一序列号
    
    Returns:
        是否添加成功
    """
    if not hash_code or len(hash_code) != 8:
        print(f" 无效的hash_code: {hash_code}")
        return False
    
    # 检查容量，超出则移除最旧的
    while len(_key_cache) >= MAX_KEY_CACHE_SIZE:
        oldest_key, oldest_info = _key_cache.popitem(last=False)
        print(f" 密钥缓存已满，移除最旧的: {oldest_key}")
    
    # 添加到缓存
    key_info = DroneKeyInfo(
        server_idx=server_idx,
        hash_code=hash_code,
        sn=sn
    )
    _key_cache[hash_code] = key_info
    print(f"密钥已缓存: hash_code={hash_code}, server={server_idx}, sn={sn}")
    
    # 从处理中队列移除
    if hash_code in _processing_keys:
        del _processing_keys[hash_code]
    
    return True


async def find_key_in_cache(hash_code: str) -> Optional[DroneKeyInfo]:
    """
    在缓存中查找密钥
    
    Args:
        hash_code: 无人机临时ID（hex字符串，8字符）
    
    Returns:
        DroneKeyInfo 如果找到，否则 None
    """
    if not hash_code:
        return None
    
    key_info = _key_cache.get(hash_code)#
    if key_info:
        # 移动到末尾（LRU策略）
        _key_cache.move_to_end(hash_code)
        return key_info
    return None


async def is_key_exists(hash_code: str) -> bool:
    """
    检查密钥是否存在于任意服务器
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        True 如果密钥存在
    """
    return hash_code in _key_cache


async def get_key_server(hash_code: str) -> Optional[int]:
    """
    获取密钥所在的服务器索引
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        服务器索引，如果密钥不存在则返回 None
    """
    key_info = await find_key_in_cache(hash_code)
    if key_info:
        return key_info.server_idx
    return None


async def get_key_sn(hash_code: str) -> Optional[str]:
    """
    获取密钥对应的序列号
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        序列号，如果不存在则返回 None
    """
    key_info = await find_key_in_cache(hash_code)
    if key_info:
        return key_info.sn
    return None


# ==================== 处理中队列管理 ====================
async def add_to_processing(hash_code: str, server_idx: int) -> bool:
    """
    将密钥添加到处理中队列
    
    带原子性检查：如果已经在处理中，返回False
    
    Args:
        hash_code: 无人机临时ID
        server_idx: 处理该密钥的服务器索引
    
    Returns:
        True 添加成功，False 已在处理中
    """
    if not hash_code:
        return False
    
    now = time.time()
    
    # 清理超时条目
    expired = [
        hc for hc, (_, ts) in _processing_keys.items()
        if now - ts > KEY_BUSY_TIMEOUT
    ]
    for hc in expired:
        del _processing_keys[hc]
        print(f" 处理中队列超时清理: {hc}")
    
    # 检查是否已在处理中
    if hash_code in _processing_keys:
        print(f"  密钥 {hash_code} 已在处理中")
        return False
    
    # 检查队列容量
    while len(_processing_keys) >= MAX_BUSY_QUEUE_SIZE:
        oldest_hc, _ = _processing_keys.popitem(last=False)
        print(f" 处理中队列已满，移除最旧条目: {oldest_hc}")
    
    _processing_keys[hash_code] = (server_idx, now)
    print(f" 密钥 {hash_code} 加入处理队列，分配服务器: {server_idx}")
    return True


async def remove_from_processing(hash_code: str) -> bool:
    """
    从处理中队列移除
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        是否移除成功
    """
    if hash_code in _processing_keys:
        del _processing_keys[hash_code]
        print(f"密钥 {hash_code} 已从处理队列移除")
        return True
    return False


async def is_in_processing(hash_code: str) -> bool:
    """
    检查密钥是否正在处理中（带超时检查）
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        True 如果正在处理中且未超时
    """
    if hash_code not in _processing_keys:
        return False
    
    # 检查是否超时
    _, timestamp = _processing_keys[hash_code]
    if time.time() - timestamp > KEY_BUSY_TIMEOUT:
        # 超时自动清理
        del _processing_keys[hash_code]
        print(f"⏰ 处理中队列超时自动清理: {hash_code}")
        return False
    
    return True


async def get_processing_server(hash_code: str) -> Optional[int]:
    """
    获取正在处理该密钥的服务器索引
    
    Args:
        hash_code: 无人机临时ID
    
    Returns:
        服务器索引，如果不在处理中则返回 None
    """
    if hash_code in _processing_keys:
        return _processing_keys[hash_code][0]
    return None


# ==================== 负载均衡核心逻辑 ====================
async def handle_key_packet(hash_code: str) -> dict:
    """
    处理密钥包的负载均衡逻辑
    
    流程：
    1. 检查密钥是否已存在（任意服务器）-> 返回 key_exist + sn
    2. 检查是否正在处理中 -> 返回 key_gen_busy 如果存在但是超时了会自动清理掉并发送到其他服务器
    3. 选择空闲服务器 -> 返回 server_idx
    4. 没有空闲服务器 -> 返回 all_servers_busy
    
    Args:
        hash_code: 无人机临时ID（hex字符串，8字符）
    
    Returns:
        {
            "action": "key_exist" | "key_gen_busy" | "dispatch" | "all_servers_busy",
            "server_idx": int (仅dispatch时有效),
            "sn": str (仅key_exist时有效)
        }
    """
    # 1. 检查密钥是否已存在
    key_info = await find_key_in_cache(hash_code)
    if key_info:
        # 密钥已存在，从处理队列中移除（防止重复请求解密）
        await remove_from_processing(hash_code)
        print(f" 密钥已存在: hash_code={hash_code}, server={key_info.server_idx}, sn={key_info.sn}")
        return {
            "action": "key_exist",
            "server_idx": key_info.server_idx,
            "sn": key_info.sn
        }
    
    # 2. 检查是否正在处理中
    if await is_in_processing(hash_code):
        processing_server = await get_processing_server(hash_code)
        print(f" 密钥正在处理中: hash_code={hash_code}, server={processing_server}")
        return {
            "action": "key_gen_busy",
            "server_idx": processing_server
        }
    
    # 3. 选择空闲服务器（自动等待重试，最多36秒）
    max_wait_attempts = 1  # 最多等待36秒（服务器繁忙超时时间）
    idle_server = get_idle_server()
    
    if not idle_server:
        # 所有服务器都繁忙，等待并重试
        print(f"⏳ 所有服务器繁忙，开始等待空闲服务器...")
        import asyncio
        
        for attempt in range(1, max_wait_attempts + 1):
            await asyncio.sleep(1)
            
            # 重新检查密钥状态（可能在等待期间已被其他请求处理）
            key_info = await find_key_in_cache(hash_code)
            if key_info:
                print(f"✅ 等待期间密钥已存在: hash_code={hash_code}, server={key_info.server_idx}")
                return {
                    "action": "key_exist",
                    "server_idx": key_info.server_idx,
                    "sn": key_info.sn
                }
            
            # 检查是否有服务器空闲
            idle_server = get_idle_server()
            if idle_server:
                print(f"✅ 等待 {attempt}s 后获得空闲服务器 {idle_server.idx}")
                break
        
    if idle_server:
        # 加入处理队列
        await add_to_processing(hash_code, idle_server.idx)
        
        print(f"📤 分发密钥包: hash_code={hash_code} -> 服务器 {idle_server.idx}")
        return {
            "action": "dispatch",
            "server_idx": idle_server.idx,
            "server_url": idle_server.url
        }
    
    # 4. 等待36秒后仍然所有服务器都繁忙
    print(f"❌ 等待 {max_wait_attempts}s 后所有服务器仍繁忙: {hash_code}")
    return {
        "action": "all_servers_busy"
    }


async def handle_data_packet(hash_code: str) -> dict:
    """
    处理数据包的负载均衡逻辑
    
    流程：
    1. 检查密钥是否存在 -> 发往对应服务器
    2. 检查是否正在处理中 -> 返回 key_gen_busy（等密钥包先处理完）
    3. 密钥不存在 -> 返回 nokey
    
    Args:
        hash_code: 无人机临时ID（hex字符串，8字符）
    
    Returns:
        {
            "action": "dispatch" | "key_gen_busy" | "nokey",
            "server_idx": int (仅dispatch时有效),
            "server_url": str (仅dispatch时有效)
        }
    """
    # 1. 检查密钥是否存在
    key_info = await find_key_in_cache(hash_code)
    if key_info:
        server = get_server(key_info.server_idx)
        # 快速路径：数据包路由无日志（高并发优化）
        return {
            "action": "dispatch",
            "server_idx": key_info.server_idx,
            "server_url": server.url if server else ""
        }
    
    # 3. 密钥不存在于服务器中（快速返回，无日志）
    return {
        "action": "nokey"
    }


async def on_keygen_result(hash_code: str, server_idx: int, success: bool, sn: str = "") -> None:
    """
    密钥包处理结果回调
    
    注意：服务器繁忙状态由36秒超时自动恢复，此处不主动设置空闲
    
    Args:
        hash_code: 无人机临时ID
        server_idx: 处理密钥的服务器索引
        success: 是否成功（繁忙也算成功）
        sn: 序列号（成功时才有）
    """
    # 从处理队列移除
    await remove_from_processing(hash_code)

    if success:
        if sn:
            #这是解密成功的回调，添加到缓存
            await add_key_to_cache(hash_code, server_idx, sn)
            #同时要将处理队列中的这个hash_code移除掉（不管成功还是失败都要移除掉，防止重复处理）
            print(f" 密钥包处理成功: hash_code={hash_code}, sn={sn}")
        #这是繁忙导致的也算成功，添加到缓存但不带sn
        else:
            await add_key_to_cache(hash_code, server_idx)
            print(f" 密钥包处理成功（密钥处理繁忙无SN）: hash_code={hash_code}")





# ==================== 统计信息 ====================
async def get_load_balancer_stats() -> dict:
    """
    获取负载均衡统计信息
    """
    server_stats = []
    for s in _servers:
        # Token状态
        token_status = "valid" if s.token else "none"
        if s.token and s.need_refresh_token():
            token_status = "expired"
        
        server_stats.append({
            "idx": s.idx,
            "url": s.url,
            "username": s.username,
            "status": "busy" if s.is_busy() else "idle",
            "token_status": token_status,
            "token_fetch_time": s.token_fetch_time.isoformat() if s.token_fetch_time else None
        })
    
    return {
        "server_count": len(_servers),
        "servers": server_stats,
        "key_cache_count": len(_key_cache),
        "key_cache_max": MAX_KEY_CACHE_SIZE,
        "processing_count": len(_processing_keys),
        "processing_max": MAX_BUSY_QUEUE_SIZE,
        "server_busy_timeout": SERVER_BUSY_TIMEOUT,
        "key_busy_timeout": KEY_BUSY_TIMEOUT,
        "token_refresh_hours": TOKEN_REFRESH_HOURS
    }


# ==================== 兼容性接口（保持与原 key_cache.py 兼容） ====================
async def is_in_keygen_succ(drone_id: str) -> bool:
    """兼容接口：检查密钥是否已存在"""
    return await is_key_exists(drone_id)


async def add_to_keygen_succ(drone_id: str, server_idx: int = 0, sn: str = "") -> bool:
    """兼容接口：添加密钥到成功缓存"""
    return await add_key_to_cache(drone_id, server_idx, sn)


async def add_to_keygen_busy(drone_id: str, server_idx: int = 0) -> bool:
    """兼容接口：添加到处理中队列"""
    return await add_to_processing(drone_id, server_idx)


async def remove_from_keygen_busy(drone_id: str) -> bool:
    """兼容接口：从处理中队列移除"""
    return await remove_from_processing(drone_id)


async def is_in_keygen_busy(drone_id: str) -> bool:
    """兼容接口：检查是否正在处理中"""
    return await is_in_processing(drone_id)
