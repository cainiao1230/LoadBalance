from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .config import settings


engine = create_async_engine(
    settings.mysql_dsn, 
    echo=False, 
    pool_pre_ping=True,
    pool_size=50,  # 常驻连接池大小，支持高并发请求
    max_overflow=50,  # 溢出连接数，峰值可达100个连接
    pool_timeout=60,  # 获取连接的超时时间60秒
    pool_recycle=3600,  # 连接回收时间1小时，防止MySQL连接过期
)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
