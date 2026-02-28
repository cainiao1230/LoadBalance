import asyncio

import httpx
from fastapi import FastAPI
import redis.asyncio as redis

from .config import settings
from . import runtime
from .routes.task_routes import router as task_router
from .routes.user_routes import router as user_router
from .worker import worker_loop, daily_cleanup_task, daily_cleanup_user_decrypt_log_task
from .rate_limiter import TokenBucketRateLimiter
from .load_balancer import init_servers, get_load_balancer_stats
from .db import engine


def create_app() -> FastAPI:
    app = FastAPI(title="Load-Balance FastAPI", version="1.0.0")
    @app.on_event("startup")
    async def on_startup():
        runtime.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        # HTTP客户端优化配置：
        # - http2=True: 启用HTTP/2多路复用（如果服务器支持，可大幅减少连接数和延迟）
        # - verify=False: 禁用SSL证书验证（内网环境）
        # - follow_redirects=False: 不自动跟随重定向
        runtime.http_b_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), 
            verify=False, 
            follow_redirects=False,
            http2=True,  # 启用HTTP/2多路复用
            limits=httpx.Limits(
                max_connections=500,          # 总连接池上限
                max_keepalive_connections=100, # 保活连接数
                keepalive_expiry=30.0         # 保活超时（秒）
            )
        )
        runtime.b_concurrency_sema = asyncio.Semaphore(settings.b_max_concurrency)
        runtime.b_rate_limiter = TokenBucketRateLimiter(settings.b_rate_limit)
        
        # 初始化负载均衡服务器列表（使用完整配置，包含账号密码）
        init_servers(settings.server_list)
        
        # 不在启动时自动创建 task 表（任务不需要存 MySQL）
        # 若需要创建表请使用迁移工具（Alembic）或在此处明确调用
        # 启动Worker并发处理密钥包任务
        # 队列中只有密钥包，Worker数量与服务器数量匹配即可
        server_count = len(settings.server_list)
        worker_count = max(server_count, 2)  # 至少2个Worker
        app.state.workers = [
            asyncio.create_task(worker_loop())
            for _ in range(worker_count)
        ]
        print(f"🚀 启动了 {worker_count} 个Worker并发处理任务")

        # 启动每日定时清理任务（保存引用，shutdown时一并取消）
        app.state.workers.append(asyncio.create_task(daily_cleanup_task()))
        app.state.workers.append(asyncio.create_task(daily_cleanup_user_decrypt_log_task()))

    @app.on_event("shutdown")
    async def on_shutdown():
        # 1. 先取消所有Worker任务
        workers = getattr(app.state, "workers", [])
        for worker in workers:
            worker.cancel()
        
        # 2. 等待所有Worker停止（最多等待2秒）
        if workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                print("Workers停止超时，强制关闭")
        
        # 3. 关闭HTTP客户端（加超时，避免HTTP/2 GOAWAY握手卡住关闭流程）
        if runtime.http_b_client:
            try:
                await asyncio.wait_for(runtime.http_b_client.aclose(), timeout=3.0)
            except Exception:
                pass
        
        # 4. 释放数据库连接池（必须在事件循环关闭前执行，否则 aiomysql __del__ 报错）
        await engine.dispose()

        # 5. 最后关闭Redis连接
        if runtime.redis_client:
            await runtime.redis_client.close()

    app.include_router(task_router)
    app.include_router(user_router)

    @app.get("/")
    async def root():
        return {"service": "Load-Balance FastAPI", "status": "ok"}
    
    @app.get("/api/server/stats")
    async def lb_stats():
        """获取负载均衡统计信息"""
        return await get_load_balancer_stats()

    return app
