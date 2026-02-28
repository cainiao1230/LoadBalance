import asyncio
import json
from datetime import datetime, timedelta

import httpx
from sqlalchemy import update, delete, select

from .config import settings
from .db import AsyncSessionLocal  # 修正为相对导入
from .models import SysUser, ServerStats, ServerKeyRelation, UserDecryptLog
from . import runtime
from .load_balancer import (
    on_keygen_result,
    get_server,
    set_server_busy,
    ServerInfo
)
from .key_cache import is_in_keygen_succ
async def get_valid_token_for_server(server: ServerInfo) -> str:
    """
    获取指定服务器的有效JWT Token，23小时自动刷新
    
    Args:
        server: 服务器信息对象
    
    Returns:
        有效的JWT Token
    """
    # 检查是否需要刷新Token
    if server.need_refresh_token():
        print(f" 刷新服务器 {server.idx} ({server.url}) 的Token...")
        
        # 调用该服务器的登录API获取新Token
        try:
            login_url = f"{server.url}/api/login"
            resp = await runtime.http_b_client.get(
                login_url,
                params={"username": server.username, "password": server.password},
                timeout=30
            )
            
            # 检查是否被重定向（301/302），说明服务器强制要求HTTPS
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_location = resp.headers.get("Location", "")
                print(f"  服务器 {server.idx} 返回重定向: {resp.status_code} -> {redirect_location}")
                raise Exception(f"服务器配置错误: URL应该使用HTTPS而不是HTTP (当前: {server.url})")
            
            resp.raise_for_status()
            data = resp.json()
            
            print(f" 服务器 {server.idx} 登录响应: success={data.get('success')}, msg='{data.get('msg')}'")
            
            if data.get("success") and "data" in data and "token" in data["data"]:
                server.update_token(data["data"]["token"])
                print(f" 服务器 {server.idx} Token刷新成功")
                print(f" Token: {server.token[:50]}...")
            else:
                error_msg = f"登录失败: {data.get('msg', 'Unknown error')}"
                print(f" 服务器 {server.idx} {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            print(f" 服务器 {server.idx} 获取Token失败: {e}")
            raise Exception(f"服务器 {server.idx} Token获取失败")
    
    if server.token is None:
        raise Exception(f"服务器 {server.idx} Token为空")
    
    return server.token


async def server_request_with_token_retry(server: ServerInfo, url: str, params: dict, timeout=30, max_retry=3):
    """
    请求指定服务器，遇到token失效时自动刷新token并重试一次。
    
    Args:
        server: 目标服务器信息
        url: 请求URL
        params: 请求参数,传进来的时候是已经有hex了
        timeout: 超时时间
        max_retry: 最大重试次数
    
    检测token失效的条件：
    1. HTTP状态码为401
    2. 响应中包含token相关错误信息
    """
    for attempt in range(max_retry + 1):
        # 获取该服务器的有效token（内部有缓存，过期才刷新）
        token = await get_valid_token_for_server(server)
        
        # 直接在params上设置token，避免每次复制字典
        params["token"] = token
        
        response = await runtime.http_b_client.get(url, params=params, timeout=timeout)
        
        # 检测是否token失效
        is_token_invalid = False
        
        # 条件1: HTTP 401
        if response.status_code == 401:
            is_token_invalid = True
            print(f" 服务器 {server.idx} 检测到401错误，token可能失效")
        
        # 条件2: 响应中包含token错误
        elif response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, dict):
                    msg = str(result.get("msg", "")).lower()
                    if "token" in msg and ("invalid" in msg or "expired" in msg or "失效" in msg):
                        is_token_invalid = True
                        print(f"服务器 {server.idx} 响应中包含token失效信息: {result.get('msg')}")
            except Exception:
                pass
        
        # 如果token失效且还有重试次数，则刷新token并重试
        if is_token_invalid and attempt < max_retry:
            print(f" 服务器 {server.idx} Token失效，强制刷新并重试... (尝试 {attempt + 1}/{max_retry + 1})")
            server.invalidate_token()
            continue
        
        # 否则返回响应
        return response
    
    return response


async def worker_loop():
    """
    工作线程主循环，从优先级队列中获取并处理任务
    
    使用Redis有序集合(sorted set)的ZPOPMIN命令获取分数最小（优先级最高）的任务
    """
    print(" Worker started!")
    if not runtime.redis_client:
        print("Redis client not initialized")
        return
    
    queue_key = "queue:priority"
    
    try:
        while True:
            try:
                # 使用ZPOPMIN获取分数最小（优先级最高）的任务
                result = await runtime.redis_client.zpopmin(queue_key, 1)
                
                if result:
                    # result格式: [(member, score)]
                    item, score = result[0]
                    job = json.loads(item)
                    print(f" Got job from queue: {job.get('task_id')}")
                    
                    # 直接处理任务
                    await process_job(job)
                else:
                    # 队列为空，短暂等待后再检查
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                # Worker被取消，正常退出
                print("✅ Worker正常停止")
                break
            except Exception as e:
                # 出现异常时等待后继续
                error_str = str(e)
                print(f"  Worker loop error: {error_str}")
                
                # 简单退避策略
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        # 外层捕获取消信号
        print("✅ Worker正常停止")
        return


async def process_job(job: dict):
    """
    处理单个解密任务
    """
    task_id = job["task_id"]
    hex_data = job.get("encrypted_data", "")#原始16进制数据
    username = job.get("username", "unknown")
    drone_id = job.get("drone_id", "")
    server_idx = job.get("server_idx", 0)  # 目标服务器索引
    start_time = datetime.now().isoformat()  # 使用本地时间

    # 设置任务为处理中状态
    if runtime.redis_client:
        await runtime.redis_client.set(
            f"task:{task_id}", 
            json.dumps({
                "status": "processing",
                "username": username,
                "start_time": start_time,
                "server_idx": server_idx  # 记录处理服务器
            }), 
            ex=settings.queue_wait_timeout
        )

    # 速率限制（每秒请求数）
    if runtime.b_rate_limiter:
        await runtime.b_rate_limiter.acquire()

    # 控制并发
    if runtime.b_concurrency_sema:
        await runtime.b_concurrency_sema.acquire()
    
    # 初始化变量（确保 finally 中可用）
    is_keygen_success = False
    KeySucc_Sn = ""
    try:
        # 获取目标服务器对象
        target_server = get_server(server_idx)
        if not target_server:
            raise Exception(f"服务器 {server_idx} 不存在")
        
        print(f" 准备处理任务: task_id={task_id}, username={username}, server={server_idx}")
        print(f"hex数据长度: {len(hex_data)}, 前40字符: {hex_data[:40]}...")
        
        # 《=========================== 更新数据库lastRequestTime ============================》
        # 从队列拿出密钥包，发往服务器之前更新最后请求时间
        try:
            async with AsyncSessionLocal() as db_session:
                result_update = await db_session.execute(
                    update(SysUser)
                    .where(SysUser.user_name == username)
                    .values(lastRequestTime=datetime.now())
                )
                await db_session.commit()
                # 检查是否更新成功（如果用户不存在，rowcount为0）
                if result_update.rowcount == 0:
                    print(f" 警告：用户 {username} 不存在，无法更新lastRequestTime")
        except Exception as db_error:
            # 数据库更新失败不应该影响主业务流程，只记录日志
            print(f"更新lastRequestTime失败: {db_error}")

        # 《===========================调用目标服务器，获取原始响应============================》
        result = await decrypt_with_retry(hex_data, target_server)#调用目标服务器解密数据，自动处理token失效重试

        # 把服务器的响应原样存入Redis，供客户端获取（保留开始时间+完成时间）
        if runtime.redis_client:
            await runtime.redis_client.set(
                f"task:{task_id}",
                json.dumps({
                    "status": "completed",
                    "data": result,
                    "username": username,
                    "start_time": start_time,
                    "finish_time": datetime.now().isoformat(),  # 使用本地时间
                    "server_idx": server_idx
                }),
                ex=settings.queue_wait_timeout,
            )
        # 情况1: 密钥包首次解密成功 - msg="keygen_succ"
        if isinstance(result, dict) and result.get("msg") == "keygen_succ":
            is_keygen_success = True
            KeySucc_Sn = result.get("sn", "")
            print(f"密钥包首次解密成功 (keygen_succ)，sn={KeySucc_Sn}")
            try:
                async with AsyncSessionLocal() as db_session:
                    # 查询 user_id
                    row = (await db_session.execute(
                        select(SysUser.user_id).where(SysUser.user_name == username)
                    )).fetchone()
                    # 更新 ServerStats 和用户解密次数
                    await db_session.execute(
                        update(ServerStats).where(ServerStats.id == server_idx)
                        .values(request_total=ServerStats.request_total + 1, key_success=ServerStats.key_success + 1)
                    )
                    await db_session.execute(
                        update(SysUser).where(SysUser.user_name == username)
                        .values(decrypt_success_count=SysUser.decrypt_success_count + 1)
                    )
                    # 插入解密日志和关联记录
                    if row:
                        db_session.add(UserDecryptLog(user_id=row.user_id, decrypt_time=datetime.now()))
                        db_session.add(ServerKeyRelation(server_id=server_idx, user_id=row.user_id, decrypt_time=datetime.now()))
                    await db_session.commit()
            except Exception as e:
                print(f"更新数据库失败: {e}")

        elif isinstance(result, dict) and result.get("msg") == "keygen_busy":
            try:
                async with AsyncSessionLocal() as db_session:
                    await db_session.execute(
                        update(ServerStats).where(ServerStats.id == server_idx)
                        .values(request_total=ServerStats.request_total + 1, keygen_busy=ServerStats.keygen_busy + 1)
                    )
                    await db_session.commit()
            except Exception as e:
                print(f"更新 ServerStats 失败: {e}")
            #需要将服务器标记为忙碌同时需要将密钥加入队列
            set_server_busy(server_idx)
            is_keygen_success = True
            print(f"密钥包解密返回 keygen_busy，服务器 {server_idx} 标记为忙碌")
        elif isinstance(result, dict) and result.get("msg")=="key_exist":
            # 需要检查当前缓存key是否存在该密钥，避免和解密服务器存的密钥不同步
            # 如果当前缓存没有该密钥，则需要加上，从而与真实服务器同步
            if drone_id:
                key_exist_sn = result.get("sn", "")
                if key_exist_sn:
                    # 标记为成功，这样 finally 中的 on_keygen_result 会将密钥加入缓存
                    is_keygen_success = True
                    KeySucc_Sn = key_exist_sn
                    print(f"密钥已存在于服务器，将同步到本地缓存: drone_id={drone_id}, sn={key_exist_sn}")
        # 情况2: 其他情况不扣费
        else:
            print(f"  不符合扣费条件，跳过扣费。返回内容: {result}")
        # ⚠ 注意：请求次数已在任务提交时（task_routes.py）累加过了
        # 这里不需要再次累加，否则会导致重复计数
    except Exception as e:
        # 处理失败，记录错误信息和完成时间
        error_detail = str(e)
        print(f"Task {task_id} failed: {error_detail}")
        error_msg = f"Task processing failed: {error_detail}"
        is_keygen_success = False  # 确保失败时不加入缓存
        KeySucc_Sn = ""
        
        if runtime.redis_client:
            await runtime.redis_client.set(
                f"task:{task_id}",
                json.dumps({
                    "status": "failed",
                    "error": error_msg,
                    "username": username,
                    "start_time": start_time,
                    "finish_time": datetime.now().isoformat()
                }),
                ex=settings.queue_wait_timeout,
            )
            
    finally:
        # 【关键】无论成功还是失败，都必须清理 _processing_keys
        # 否则 drone_id 会永久卡在处理中队列里，导致后续请求一直返回 key_gen_busy
        if drone_id:
            await on_keygen_result(
                hash_code=drone_id,
                server_idx=server_idx,
                success=is_keygen_success,
                sn=KeySucc_Sn
            )
        
        # 释放并发信号量
        if runtime.b_concurrency_sema:
            runtime.b_concurrency_sema.release()


async def decrypt_with_retry(hex_data: str, server: ServerInfo):
    """
    调用目标服务器解密数据
    
    Args:
        hex_data: 16进制数据
        server: 目标服务器信息对象（包含URL、账号、Token等）
    """
    # 使用缓存的URL，避免每次拼接
    if not hasattr(server, '_decrypt_url'):
        server._decrypt_url = f"{server.url}/api/yd/decryptl"
    decrypt_url = server._decrypt_url

    # 打印完整的请求信息（hex数据截取前20字符）
    print(f"请求服务器 {server.idx}: URL={decrypt_url}, hex={hex_data[:40]}...")
    
    # 调用目标服务器，自动处理token失效重试
    response = await server_request_with_token_retry(
        server=server,
        url=decrypt_url,
        params={"hex": hex_data},
        timeout=30,
        max_retry=1
    )
    
    # 打印完整的请求URL（包含参数，但token只显示前20字符）
    actual_url = str(response.url)
    if len(actual_url) > 300:
        # 如果URL太长，截取关键部分显示
        print(f"📡 实际请求: {actual_url[:150]}...{actual_url[-50:]}")
    else:
        print(f"📡 实际请求: {actual_url}")

    # 检查HTTP状态码
    if response.status_code != 200:
        error_detail = f"服务器 {server.idx} 返回错误: HTTP {response.status_code}"
        print(f" {error_detail}")
        print(f"   响应内容: {response.text[:200]}")  # 只打印前200字符

    # 解析响应
    try:
        result = response.json()
        return result
    except Exception as e:
        print(f"服务器 {server.idx} 响应解析失败: {e}")
        raise Exception(f"服务器响应格式错误: {str(e)}")


async def cleanup_old_server_keys(db_session):
    """
    清理 server_key_relation 表中过期（30天前）的数据
    """
    threshold_date = datetime.now() - timedelta(days=30)
    await db_session.execute(
        delete(ServerKeyRelation).where(ServerKeyRelation.decrypt_time < threshold_date)
    )
    await db_session.commit()


async def daily_cleanup_task():
    """
    每天凌晨前1秒自动清理 server_key_relation 表中过期（30天前）数据
    """
    while True:
        now = datetime.now()
        # 计算距离明天凌晨0点0分0秒还有多少秒
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = (tomorrow - now).total_seconds()
        # 提前1秒
        sleep_seconds = max(0, seconds_until_midnight - 1)
        print(f"[定时清理] 距离下次清理还有 {sleep_seconds} 秒")
        await asyncio.sleep(sleep_seconds)
        try:
            async with AsyncSessionLocal() as db_session:
                await cleanup_old_server_keys(db_session)
            print(f"[定时清理] {datetime.now()} 已完成 server_key_relation 30天数据清理")
        except Exception as e:
            print(f"[定时清理] 清理 server_key_relation 失败: {e}")
        # 等待1秒，确保不会重复清理
        await asyncio.sleep(1)

async def cleanup_old_user_decrypt_log(db_session):
    """
    清理 user_decrypt_log 表中过期（3天前）的数据
    """
    threshold_date = datetime.now() - timedelta(days=3)
    await db_session.execute(
        delete(UserDecryptLog).where(UserDecryptLog.decrypt_time < threshold_date)
    )
    await db_session.commit()


async def daily_cleanup_user_decrypt_log_task():
    """
    每天凌晨前1秒自动清理 user_decrypt_log 表中过期（3天前）数据
    """
    while True:
        now = datetime.now()
        # 计算距离明天凌晨0点0分0秒还有多少秒
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = (tomorrow - now).total_seconds()
        # 提前1秒
        sleep_seconds = max(0, seconds_until_midnight - 1)
        print(f"[定时清理] 距离下次 user_decrypt_log 清理还有 {sleep_seconds} 秒")
        await asyncio.sleep(sleep_seconds)
        try:
            async with AsyncSessionLocal() as db_session:
                await cleanup_old_user_decrypt_log(db_session)
            print(f"[定时清理] {datetime.now()} 已完成 user_decrypt_log 3天数据清理")
        except Exception as e:
            print(f"[定时清理] 清理 user_decrypt_log 失败: {e}")
        # 等待1秒，确保不会重复清理
        await asyncio.sleep(1)

# 在主入口（如 worker_loop 启动前）加上：
# asyncio.create_task(daily_cleanup_task())
# 这样服务只需启动一次，每天凌晨前1秒自动清理，无需人工干预。

# asyncio.create_task(daily_cleanup_user_decrypt_log_task())
# 这样服务只需启动一次，每天凌晨前1秒自动清理 user_decrypt_log 表，无需人工干预。

