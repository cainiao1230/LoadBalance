import asyncio
import time


class TokenBucketRateLimiter:
    """
    令牌桶速率限制器
    用于控制每秒请求数
    """

    def __init__(self, rate: int):
        """
        初始化令牌桶
        
        Args:
            rate: 每秒允许的请求数
        """
        self.rate = rate
        self.tokens = rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        获取一个令牌，如果没有令牌则等待
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            
            # 补充令牌
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return
            
            # 等待直到有令牌
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
