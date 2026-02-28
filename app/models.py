from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, BigInteger, DateTime, Text, CHAR, Column, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SysUser(Base):
    __tablename__ = "sys_user"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment='用户ID')
    user_name: Mapped[str] = mapped_column(String(30), unique=True, index=True, comment='用户账号')
    phonenumber: Mapped[Optional[str]] = mapped_column(String(11), default="", comment='手机号码')
    sex: Mapped[Optional[str]] = mapped_column(CHAR(1), default="0", comment='用户性别（0男 1女 2未知）')
    password: Mapped[str] = mapped_column(String(100), default="", comment='密码')
    status: Mapped[str] = mapped_column(CHAR(1), default="0", comment='账号状态（0正常 1停用）')
    login_ip: Mapped[Optional[str]] = mapped_column(String(128), default="", comment='最后登录IP')
    login_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='最后登录时间')
    pwd_update_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='密码最后更新时间')
    priority: Mapped[int] = mapped_column(Integer, default=1, comment='优先级（数字越小优先级越高）')
    remaining_requests: Mapped[int] = mapped_column(Integer, default=0, comment='剩余请求次数（-1表示无限制）')
    total_requests: Mapped[int] = mapped_column(Integer, default=-1, comment='总请求次数（最初分配的请求次数，-1表示无限制）')
    create_by: Mapped[Optional[str]] = mapped_column(String(64), default="admin", comment='创建者')
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='创建时间')
    update_by: Mapped[Optional[str]] = mapped_column(String(64), default="admin", comment='更新者')
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='这个字段只会在更新优先级和创建优先级的情况下改变')
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment='备注')
    lastRequestTime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='最后一次请求时间')
    totalUpdateTime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment='总数更新时间')
    decrypt_success_count: Mapped[int] = mapped_column(Integer, default=0, comment='成功解密次数')


class ServerStats(Base):
    __tablename__ = "server_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, comment="服务器IP")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="账号")
    password: Mapped[str] = mapped_column(String(128), nullable=False, comment="密码")
    keygen_busy: Mapped[int] = mapped_column(Integer, default=0, comment="keygen_busy次数")
    key_success: Mapped[int] = mapped_column(Integer, default=0, comment="key_success次数")
    request_total: Mapped[int] = mapped_column(Integer, default=0, comment="请求总数")


class ServerKeyRelation(Base):
    __tablename__ = "server_key_relation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="服务器ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('sys_user.user_id'), nullable=False, comment="用户ID")
    decrypt_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="解密时间")


class UserDecryptLog(Base):
    __tablename__ = 'user_decrypt_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('sys_user.user_id'), nullable=False)
    decrypt_time = Column(DateTime, default=datetime.now, nullable=False)
