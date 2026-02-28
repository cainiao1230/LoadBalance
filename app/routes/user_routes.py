# 导入用于可逆解密的AES库
import base64
from typing import Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 导入FastAPI相关依赖
from fastapi import APIRouter, Depends, Query, Request
# 导入SQLAlchemy用于数据库操作的select
from sqlalchemy import select
# 导入异步数据库会话
from sqlalchemy.ext.asyncio import AsyncSession

# 导入自定义的数据库依赖、模型和配置
from ..db import get_db
from ..models import SysUser
from ..config import settings


def decrypt_password(ciphertext_b64: str) -> str | None:
    """解密密码（AES/CBC/PKCS5 Base64）"""
    try:
        key = settings.aes_key.encode("utf-8")
        iv = settings.aes_iv.encode("utf-8")
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(base64.b64decode(ciphertext_b64)), AES.block_size)
        return plaintext.decode("utf-8")
    except Exception:
        return None


# 创建API路由器，前缀为/api，标签为users
router = APIRouter(prefix="/api", tags=["users"])


# 定义/query/persondata接口，查询用户请求次数
@router.get("/query/persondata")
async def query_user_requests(
    request: Request,
    username: Optional[str] = Query(None, description="用户名"),
    password: Optional[str] = Query(None, description="密码"),
    db: AsyncSession = Depends(get_db)
):
    """查询用户请求次数
    
    访问示例：http://localhost:8765/api/query/persondata?username=ceshi1&password=123456
    
    Args:
        request: 请求对象
        username: 用户名（必需）
        password: 密码（必需）
        db: 数据库会话
    
    Returns:
        返回JSON格式：
        成功: {"code": 200, "message": "成功", "data": {"visitTimes": "100/1000"}}
        失败: {"code": 400/401/403, "message": "错误信息", "data": {}}
    """
    # 检查参数数量 - 只允许username和password两个参数
    query_params = dict(request.query_params)
    allowed_params = {"username", "password"}
    actual_params = set(query_params.keys())
    # 检查是否有多余的参数
    extra_params = actual_params - allowed_params
    if extra_params:
        return {
            "code": 400,
            "message": f"Invalid parameters: {', '.join(extra_params)}",
            "data": {}
        }
    # 检查是否缺少必需参数
    missing_params = allowed_params - actual_params
    if missing_params:
        return {
            "code": 400,
            "message": f"Missing required parameters: {', '.join(missing_params)}",
            "data": {}
        }
    
    # 参数校验 - 检查username是否为空
    if username is None or username.strip() == "":
        return {
            "code": 400,
            "message": "Username cannot be empty",
            "data": {}
        }
    
    # 参数校验 - 检查password是否为空
    if password is None or password.strip() == "":
        return {
            "code": 400,
            "message": "Password cannot be empty",
            "data": {}
        }
    
    # 根据用户名查询用户（去除首尾空格）
    username = username.strip()
    
    try:
        res = await db.execute(select(SysUser).where(SysUser.user_name == username))
        user: SysUser | None = res.scalar_one_or_none()
    except Exception as e:
        return {
            "code": 500,
            "message": f"Service error: {str(e)}",
            "data": {}
        }
    
    # 用户不存在
    if not user:
        return {
            "code": 401,
            "message": "User not found",
            "data": {}
        }
    
    # 验证密码（AES/CBC/PKCS5 Base64解密）
    decrypted = decrypt_password(user.password)
    if not decrypted or decrypted != password:
        return {
            "code": 401,
            "message": "Invalid password",
            "data": {}
        }
    
    # 检查用户状态
    if user.status == "1":
        return {
            "code": 403,
            "message": "User account disabled",
            "data": {}
        }
    
    # 获取已用次数和总次数
    remaining_requests =user.remaining_requests
    total_requests = user.total_requests
    
    # 如果total_requests为-1，返回次数无限制
    if total_requests is not None and total_requests == -1:
        return {
            "code": 200,
            "message": "Success",
            "data": {
                "visitTimes": "unlimited"
            }
        }
    
    # 返回格式：剩余次数/总次数（字符串）
    remaining = remaining_requests if remaining_requests is not None else 0
    total = total_requests if total_requests is not None else 0
    return {
        "code": 200,
        "message": "Success",
        "data": {
            "visitTimes": f"{remaining}/{total}"
        }
    }
