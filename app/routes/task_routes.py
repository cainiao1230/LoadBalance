# 导入用于生成唯一任务ID的uuid库
import uuid
# 导入用于可逆解密的AES库
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
# 导入用于异步操作的asyncio
import asyncio
import json
import time
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta
# 导入JWT库
import jwt

from ..db import AsyncSessionLocal
from ..models import ServerStats, UserDecryptLog, SysUser # 确保已导入 ServerStats
# 导入FastAPI相关依赖
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
# 导入SQLAlchemy用于数据库操作的select
from sqlalchemy import select, update
# 导入异步数据库会话
from sqlalchemy.ext.asyncio import AsyncSession


# 导入自定义的数据库依赖、模型、数据结构和任务服务
from ..db import get_db
from ..models import SysUser
from ..schemas import SubmitResponse, QuickSubmitRequest, OptimizedSubmitResponse, LoginResponse
from ..task_service import push_task_to_queue
from ..config import settings
from ..packet_parser import parse_packet
from ..load_balancer import (
    handle_key_packet, 
    handle_data_packet,
    find_key_in_cache,
    init_servers,
    remove_from_processing,
    get_server
)
from ..worker import decrypt_with_retry, get_valid_token_for_server


# Token过期时间：48小时（秒）
TOKEN_EXPIRE_SECONDS = 48 * 60 * 60

# JWT密钥（用于签名token），从配置中加载
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "ApiStore"
JWT_AUDIENCE = "ApiStore"


def decrypt_password(ciphertext_b64: str) -> str | None:
    try:
        key = settings.aes_key.encode("utf-8")
        iv = settings.aes_iv.encode("utf-8")
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(base64.b64decode(ciphertext_b64)), AES.block_size)
        return plaintext.decode("utf-8")
    except Exception:
        return None
from .. import runtime


# 创建API路由器，前缀为/api，标签为tasks
router = APIRouter(prefix="/api", tags=["tasks"])


async def _charge_user(username: str) -> tuple[bool, int]:
    """异步扣费，使用原子操作防止超额
    
    Returns:
        (bool, int): (扣费是否成功, 扣费后的remaining_requests)
    """
    try:
        async with AsyncSessionLocal() as charge_db:
            # 原子操作：只有在剩余次数>0时才扣费（防止并发超额）
            result = await charge_db.execute(
                update(SysUser)
                .where(
                    SysUser.user_name == username,
                    # total_requests=-1表示无限制，跳过检查
                    # 否则必须满足：remaining_requests < total_requests
                    (SysUser.total_requests == -1) | (SysUser.remaining_requests < SysUser.total_requests)
                )
                .values(remaining_requests=SysUser.remaining_requests + 1)
            )
            await charge_db.commit()
            
            # 检查是否有行被更新（0表示余额不足，扣费失败）
            if result.rowcount > 0:
                # 查询更新后的值
                res = await charge_db.execute(
                    select(SysUser.remaining_requests).where(SysUser.user_name == username)
                )
                new_remaining = res.scalar_one_or_none()
                return (True, new_remaining or 0)
            return (False, -1)
    except Exception as e:
        print(f"  扣费失败: {e}")
        return (False, -1)


async def generate_user_token(username: str) -> str:
    """为用户生成JWT格式的token并存储到Redis
    
    生成固定长度355字符的JWT token，包含用户名、角色、过期时间等信息。
    Token绑定用户名，且每次生成都是唯一的。
    
    Args:
        username: 用户名
    
    Returns:
        生成的JWT token字符串（固定355字符）
    """
    # 计算过期时间
    exp_time = datetime.utcnow() + timedelta(seconds=TOKEN_EXPIRE_SECONDS)
    exp_timestamp = int(exp_time.timestamp())
    
    # 生成唯一标识（5字符，确保同一用户多次登录生成不同token）
    unique_id = hashlib.md5(f"{username}:{time.time()}:{secrets.token_hex(4)}".encode()).hexdigest()[:5]
    
    # 用户名填充到固定8字符（确保token长度固定为355字符）
    padded_username = username.ljust(8)[:8]
    
    # 构建JWT payload（模拟.NET风格的claims）
    payload = {
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": padded_username,
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "0",
        "exp": exp_timestamp,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": unique_id,  # JWT ID，确保唯一性
    }
    
    # 生成JWT token（固定355字符）
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # 存储到Redis，key为 user_token:{token}，value为原始用户名
    if runtime.redis_client:
        await runtime.redis_client.setex(
            f"user_token:{token}",
            TOKEN_EXPIRE_SECONDS,
            username  # 存储原始用户名（不含填充）
        )
    
    return token


# 内存缓存：token -> (username, expire_time)，避免每次都查Redis
_token_cache: dict = {}
# ⚠️ 不缓存用户对象，配额信息(remaining/total_requests)需要实时准确


def _build_json_response(result) -> Response:
    """将解密结果以 text/plain 格式返回（带缩进，与截图一致）"""
    if isinstance(result, (dict, list)):
        content = json.dumps(result, indent=2, ensure_ascii=False)
    elif isinstance(result, str):
        # 尝试解析，确保是合法JSON
        try:
            parsed = json.loads(result)
            content = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            content = result  # 原样返回
    else:
        content = json.dumps(result, indent=2, ensure_ascii=False)

    return Response(content=content, media_type="text/plain; charset=utf-8")


async def validate_token(token: str) -> Optional[str]:
    """验证token并返回对应的用户名（带内存缓存）"""
    # 1. 先查内存缓存
    cached = _token_cache.get(token)
    if cached:
        username, expire_ts = cached
        if time.time() < expire_ts:
            return username
        else:
            del _token_cache[token]  # 过期清理
    
    # 2. 缓存未命中，查Redis
    if not runtime.redis_client:
        return None
    
    username = await runtime.redis_client.get(f"user_token:{token}")
    if username:
        username = username.decode("utf-8") if isinstance(username, bytes) else username
        # 缓存到内存（30分钟有效，匹配用户缓存时长）
        _token_cache[token] = (username, time.time() + 1800)
        return username
    return None


async def get_user(username: str, db: AsyncSession = None) -> Optional[SysUser]:
    """获取用户信息（实时查询，不缓存配额）
    
    Args:
        username: 用户名
        db: 数据库会话（可选）
    
    Returns:
        用户对象或None
    """
    # 每次都查数据库，确保配额信息准确（数据库有连接池+索引，性能足够）
    if db is None:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(SysUser).where(SysUser.user_name == username))
            return res.scalar_one_or_none()
    else:
        res = await db.execute(select(SysUser).where(SysUser.user_name == username))
        return res.scalar_one_or_none()


async def get_user_orders(user: SysUser) -> list:
    """获取用户订单信息（请求次数）
    
    Args:
        user: 用户对象
    
    Returns:
        订单列表
    """
    # 构建订单信息：显示已使用次数/总次数
    if user.total_requests == -1:
        # 无限制
        order_detail = f"{user.remaining_requests}/unlimited"
    else:
        used = user.remaining_requests
        total = user.total_requests
        order_detail = f"{used}/{total}"
    
    return [f"{user.user_name}: {order_detail}"]


async def wait_for_task_result(task_id: str, max_wait: int = None) -> dict:
    """等待任务完成并返回结果
    
    Args:
        task_id: 任务ID
        max_wait: 最大等待时间（秒），默认使用 settings.queue_wait_timeout
    
    Returns:
        包含status和decrypted_data的字典
    
    Raises:
        HTTPException: 任务失败或超时时抛出
    """
    if max_wait is None:
        max_wait = settings.queue_wait_timeout
    
    start_time = time.time()
    
    while True:
        # 检查是否超时
        elapsed = time.time() - start_time
        if elapsed >= max_wait:
            print(f" Task {task_id} wait timeout after {elapsed:.1f}s")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server busy, please retry later",
            )
        
        # 从Redis获取任务状态
        if runtime.redis_client:
            result = await runtime.redis_client.get(f"task:{task_id}")
            
            # key 不存在 = 已超时自动过期，返回服务器繁忙
            if result is None:
                print(f" Redis key expired for task: {task_id}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Server busy, please retry later",
                )
            
            data = json.loads(result)# 解析任务结果JSON
            task_status = data.get("status")

            if task_status == "completed":
                return data
            
            # 任务处理失败
            if task_status == "failed":
                error_msg = data.get("error", "Task processing failed")
                # 打印完整错误到日志
                print(f" Task {task_id} failed: {error_msg}")
                # 返回通用错误给客户端，隐藏服务器详情
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Task processing failed",
                )
        
        # 等待一段时间后重试（间隔越短响应越快，但CPU开销越大）
        await asyncio.sleep(0.05)


# ==================== 登录接口 ====================
@router.get("/login", response_model=LoginResponse)
async def login(
    username: str = Query(..., description="用户名"),#从query参数获取用户名
    password: str = Query(..., description="密码"),#从query参数获取密码
    db: AsyncSession = Depends(get_db)
):
    """登录接口：验证用户名密码，返回token
    
    这一步只是为了获取token，每24小时只需要申请一次。
    
    访问示例：http://localhost:8765/api/task/login?username=用户名&password=密码
    
    Returns:
        成功: {"success": true, "msg": "", "data": {"token": "xxx", "orders": ["用户名: 已用次数/总次数"]}}
        失败: {"success": false, "msg": "错误信息", "data": null}
    """
    # 校验用户身份：根据用户名查找用户（去除首尾空格）
    username = username.strip() if username else ""
    res = await db.execute(select(SysUser).where(SysUser.user_name == username))
    user: SysUser | None = res.scalar_one_or_none()
    
    # 检查用户是否存在且状态正常
    if not user or user.status != "0":
        return LoginResponse(
            success=False,
            msg="User not found or account disabled",
            data=None
        )
    
    # 校验密码是否正确（AES/CBC/PKCS5 Base64）
    decrypted = decrypt_password(user.password)
    if not decrypted or decrypted != password:
        return LoginResponse(
            success=False,
            msg="Invalid password",
            data=None
        )
    
    # 生成token
    token = await generate_user_token(username)
    
    # 获取订单信息
    orders = await get_user_orders(user)
    
    return LoginResponse(
        success=True,
        msg="",
        data={
            "token": token,
            "orders": orders
        }
    )


# ==================== 解密接口（支持两种认证方式） ====================
@router.get("/yd/decryptl")
async def quick_submit(
    hex: str = Query(..., description="16进制数据"),
    username: Optional[str] = Query(None, description="用户名（方式一）"),
    password: Optional[str] = Query(None, description="密码（方式一）"),
    token: Optional[str] = Query(None, description="登录token（方式二）")
):
    """解密接口：支持两种认证方式
    
    方式一：用户名 + 密码 + hex
        http://localhost:5000/api/yd/decryptl?username=xxx&password=xxx&hex=xxx
    
    方式二：token + hex（token从登录接口获取，24小时有效，性能更优）
        http://localhost:5000/api/yd/decryptl?token=xxx&hex=xxx
    """
    user: SysUser | None = None
    
    # ========== 认证逻辑 ==========
    # 方式二：token认证（优先检查，token缓存避免查Redis）
    if token:
        validated_username = await validate_token(token)
        if not validated_username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid or expired token"
            )
        # 实时查询用户信息（确保配额准确，数据库连接池性能足够）
        user = await get_user(validated_username)
        if not user or user.status != "0":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User not found or account disabled"
            )
    
    # 方式一：用户名+密码认证（需要数据库查询）
    elif username and password:
        # 获取数据库连接
        async with AsyncSessionLocal() as db:
            # 校验用户身份：根据用户名查找用户（去除首尾空格）
            username = username.strip()
            res = await db.execute(select(SysUser).where(SysUser.user_name == username))
            user = res.scalar_one_or_none()
            # 检查用户是否存在且状态正常
            if not user or user.status != "0":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="User not found or account disabled"
                )
            # 校验密码是否正确（AES/CBC/PKCS5 Base64）
            decrypted = decrypt_password(user.password)
            if not decrypted or decrypted != password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid password"
                )
    
    else:
        # 既没有token也没有username+password
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication required: username+password or token"
        )
    
    # ========== 解析数据包 ==========
    try:
        packet_info = parse_packet(hex)
        # 检查是否为有效数据包
        if not packet_info['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="useless packet"
            )
        
        # 提取包类型信息（解包只用于判断，发送给B服务器的是原始数据）
        raw_hex = packet_info['raw_bytes'].hex()  # 原始176字节（发给B服务器）
        packet_type = packet_info['packet_type']
        is_key_packet = packet_info['is_key_packet']
        drone_id = packet_info['drone_id']  # hash_code，8位hex字符串
        
        if is_key_packet:
            print(f" 数据包解析: 类型={packet_type}, 无人机ID={drone_id}, 密钥包=是")
        
        # ========== 请求次数检查（实时查询+同步扣费）==========
        # 重新查询数据库获取最新配额（管理员可能随时修改）
        fresh_user = await get_user(user.user_name)
        if fresh_user:
            user = fresh_user  # 使用最新的用户信息
        
        if user.total_requests is not None and user.total_requests != -1:
            # 预检：已用次数达到或超过总配额时拒绝
            if user.remaining_requests >= user.total_requests:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Request quota exceeded"
                )
            
            # 同步扣费：使用原子操作确保不会超过total_requests
            charge_success, _ = await _charge_user(user.user_name)
            if not charge_success:
                # 扣费失败说明配额已用完（可能是并发请求导致）
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Request quota exceeded"
                )
        
        # ========== 负载均衡处理 ==========
        server_idx = 0  # 默认服务器索引
        max_wait_attempts = 36  # 最多等待36秒
        if is_key_packet:
            # 密钥包：检查是否已存在或正在处理
            lb_result = await handle_key_packet(drone_id)
            action = lb_result.get("action")
            
            if action == "key_exist":
                # 密钥已存在，直接返回 key_exist 和 sn
                sn = lb_result.get("sn", "")
                print(f" 密钥已存在: drone_id={drone_id}, sn={sn}")
                return {
                    "msg": "key_exist",
                    "sn": sn
                }
            
            elif action == "key_gen_busy":
                # 正在处理中
                print(f" 密钥正在处理队列中: drone_id={drone_id}")
                return {
                    "msg": "key_gen_busy",
                    "note": "The key package is in queue"
                }
            
            elif action == "all_servers_busy":
                # 所有服务器繁忙，等待重试
                print(f"  所有服务器繁忙，开始等待...")
                for attempt in range(max_wait_attempts):
                    await asyncio.sleep(1)
                    lb_result = await handle_key_packet(drone_id)
                    action = lb_result.get("action")
                    
                    if action == "key_exist":
                        sn = lb_result.get("sn", "")
                        print(f" 等待期间密钥已存在: drone_id={drone_id}")
                        return {"msg": "key_exist", "sn": sn}
                    
                    elif action == "dispatch":
                        server_idx = lb_result.get("server_idx", 0)
                        print(f" 等待 {attempt + 1}s 后获得空闲服务器 {server_idx}")
                        break
                    
                    elif action == "key_gen_busy":
                        print(f" 密钥已在处理中: drone_id={drone_id}")
                        return {"msg": "key_gen_busy", "note": "waiting 36s and try again."}
                    
                    print(f"⏳ 等待空闲服务器... ({attempt + 1}/{max_wait_attempts}s)")
                else:
                    # 等待超时，仍然全忙
                    print(f" 等待 {max_wait_attempts}s 后仍无空闲服务器")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="All servers busy, please retry later"
                    )
            
            elif action == "dispatch":
                # 分发到指定服务器
                server_idx = lb_result.get("server_idx", 0)
                print(f" 密钥包分发到服务器 {server_idx}: drone_id={drone_id}")
        
        else:
            # ========== 数据包：直接调用解密服务器，不走队列 ==========
            lb_result = await handle_data_packet(drone_id)
            action = lb_result.get("action")
            
            if action == "nokey":
                # 密钥不存在（快速返回，无日志）
                return {
                    "msg": "no_key"
                }
            elif action == "dispatch":
                # 直接发往密钥所在服务器，跳过队列（快速路径，无日志）
                server_idx = lb_result.get("server_idx", 0)
                try:
                    target_server = get_server(server_idx)
                    if not target_server:
                        raise Exception(f"服务器 {server_idx} 不存在")
                    
                    # 《=========================== 更新数据库lastRequestTime ============================》
                    # 数据包不排队，直接发往服务器之前更新最后请求时间
                    try:
                        async with AsyncSessionLocal() as update_db:
                            result_update = await update_db.execute(
                                update(SysUser)
                                .where(SysUser.user_name == user.user_name)
                                .values(lastRequestTime=datetime.now())
                            )
                            await update_db.commit()
                            # 检查是否更新成功
                            if result_update.rowcount == 0:
                                print(f"警告：用户 {user.user_name} 不存在，无法更新lastRequestTime")
                    except Exception as db_error:
                        # 数据库更新失败不应该影响主业务流程，只记录日志
                        print(f"更新lastRequestTime失败: {db_error}")
                    # 《=========================== 更新服务器请求总数 ============================》
                    try:
                        result_server_update = await update_db.execute(
                            update(ServerStats)
                            .where(ServerStats.id == server_idx)
                            .values(request_total=ServerStats.request_total + 1)
                        )
                        # 新增：插入用户解密日志
                        update_db.add(UserDecryptLog(user_id=user.user_id, decrypt_time=datetime.now()))
                        await update_db.commit()

                        if result_server_update.rowcount == 0:
                            print(f"警告：服务器 {server_idx} 不存在，无法更新 request_total")
                    except Exception as server_db_error:
                        print(f"更新服务器 request_total 失败: {server_db_error}")
                    # 直接调用解密服务器
                    result = await decrypt_with_retry(raw_hex, target_server)
                    # 直接返回解密结果（零延迟，扣费已在前面统一处理）
                    return _build_json_response(result)
                    
                except Exception as e:
                    print(f"数据包直接解密失败: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Task processing failed"
                    )
    except ValueError as e:
        # 数据包长度或格式错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid packet format: {str(e)}"
        )

    # ========== 以下仅密钥包走队列 ==========
    # 直接从SysUser表获取优先级和更新时间
    priority = user.priority if hasattr(user, 'priority') else 10
    update_time = user.update_time if hasattr(user, 'update_time') else None

    # 生成唯一任务ID
    task_id = uuid.uuid4().hex

    # 推送密钥包到消息队列，附带优先级
    try:
        await push_task_to_queue(
            {
                "task_id": task_id,
                "username": user.user_name,
                "priority": priority,
                "update_time": str(update_time) if update_time else "",
                "encrypted_data": raw_hex,
                "packet_type": packet_type,
                "is_key_packet": is_key_packet,
                "drone_id": drone_id,
                "server_idx": server_idx,
            },
            priority,
        )
    except Exception as e:
        # 入队失败，回滚负载均衡状态
        if is_key_packet and drone_id:
            await remove_from_processing(drone_id)
            print(f"任务入队失败，已回滚负载均衡状态: {drone_id}")
        raise

    # ========== 等待密钥包处理完成（可选：支持快速返回模式）==========
    # 注意：如果需要极致性能，可以直接返回task_id让客户端轮询
    # return {"task_id": task_id, "status": "processing"}
    
    try:
        result = await wait_for_task_result(task_id)
        
        b_server_response = result.get("data", {})
        response_data = {}
        
        if isinstance(b_server_response, dict):
            response_data.update(b_server_response)
        elif isinstance(b_server_response, str):
            try:
                parsed_data = json.loads(b_server_response)
                if isinstance(parsed_data, dict):
                    response_data.update(parsed_data)
                else:
                    response_data["data"] = parsed_data
            except json.JSONDecodeError:
                response_data["data"] = b_server_response
        else:
            response_data["data"] = b_server_response
        
        return _build_json_response(response_data)
    except HTTPException:
        raise