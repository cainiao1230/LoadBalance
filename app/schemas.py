from pydantic import BaseModel
from typing import Optional, Any, List


class QuickSubmitRequest(BaseModel):
    username: str
    password: str
    encrypted_data: str


class SubmitResponse(BaseModel):
    task_id: str
    status: str
    decrypted_data: Optional[str] = None
    error: Optional[str] = None
    username: Optional[str] = None  # 任务所属用户
    start_time: Optional[str] = None  # 开始处理时间
    finish_time: Optional[str] = None  # 完成时间


class OptimizedSubmitResponse(BaseModel):
    """优化后的响应格式：直接展开解密数据的字段"""
    task_id: str
    
    class Config:
        extra = "allow"  # 允许额外字段，用于展开解密数据


class OrderInfo(BaseModel):
    """订单信息"""
    order_id: str
    order_detail: str


class LoginResponse(BaseModel):
    """登录响应格式"""
    success: bool
    msg: str
    data: Optional[dict] = None
