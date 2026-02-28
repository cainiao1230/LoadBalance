import asyncio
from typing import Optional

import httpx
import redis.asyncio as redis

redis_client: Optional[redis.Redis] = None  # Redis 负责队列、缓存、统计
http_b_client: Optional[httpx.AsyncClient] = None  # 转发到服务器的 httpx 客户端
b_concurrency_sema: Optional[asyncio.Semaphore] = None  # 控制同时打到服务器的并发数
last_low_dispatch_ts: float = 0.0  # 普通队列上次派发时间，用于 1 req/s 限速

# 速率限制
b_rate_limiter: Optional[object] = None  # 服务器请求速率限制器
