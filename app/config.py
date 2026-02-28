import os
import json
from pydantic import BaseModel
from typing import List, Dict


class ServerConfig(BaseModel):
    """单台服务器配置"""
    url: str                    # 服务器URL
    username: str               # 登录账号
    password: str               # 登录密码


class Settings(BaseModel):
    mysql_dsn: str = os.getenv(
        "MYSQL_DSN",
        "mysql+aiomysql://root:123456@192.0.2.1:3306/decrypt-serve-admin",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://:123456@192.0.2.1:6379/0")
    #admin
    #5GDiLRnTnHcaLnJN
    b_url: str = os.getenv("B_URL", "https://192.0.2.1/api/yd/decryptl?hex={HEX_DATA}&token={TOKEN}")
    admin_token: str = os.getenv("ADMIN_TOKEN", "admin-secret")
    b_max_concurrency: int = int(os.getenv("B_MAX_CONCURRENCY", "200"))  # 打B的最大并发，匹配速率限制
    b_rate_limit: int = int(os.getenv("B_RATE_LIMIT", "200"))  # 打B的每秒请求数限制
    queue_wait_timeout: int = int(os.getenv("QUEUE_WAIT_TIMEOUT", "300"))  # 队列等待超时5分钟，避免长时间堆积
    max_queue_size: int = int(os.getenv("MAX_QUEUE_SIZE", "200"))  # 队列最大长度
    aes_key: str = os.getenv("AES_KEY", "RuoYi@2026#Key!!")
    aes_iv: str = os.getenv("AES_IV", "RuoYi@InitVector")
    jwt_secret_key:str=os.getenv("JWT_SECRET_KEY","ApiStore_SecretKey_2026_LoadBalance_System")
    
    # 负载均衡配置：多服务器列表（JSON格式）
    # 格式：[{"url": "https://server1.com", "username": "user1", "password": "pass1"}, ...]
    # 示例环境变量：
    # SERVERS_CONFIG='[{"url":"https://192.0.2.1","username":"wtx2","password":"364sdfoLdf"},{"url":"https://xxx.xxx.xxx.xxx","username":"user2","password":"pass2"}]'
    servers_config: str = os.getenv(
        "SERVERS_CONFIG",
        '[{"url":"https://192.0.2.1","username":"xingxun","password":"xingxun123"},{"url":"https://192.0.2.1","username":"wtx2","password":"364sdfoLdf"},{"url":"http://192.0.2.1:5000","username":"wtx3","password":"fertokKH390"}]'  #
    )
    
    # 服务器繁忙超时时间（秒），处理密钥包时设置
    server_busy_timeout: int = int(os.getenv("SERVER_BUSY_TIMEOUT", "36"))
    
    # Token刷新间隔（小时）
    token_refresh_hours: int = int(os.getenv("TOKEN_REFRESH_HOURS", "23"))
    
    @property
    def server_list(self) -> List[ServerConfig]:
        """解析服务器配置列表"""
        try:
            configs = json.loads(self.servers_config)
            return [ServerConfig(**cfg) for cfg in configs]
        except Exception as e:
            print(f"⚠️  解析服务器配置失败: {e}，使用默认配置")
            return [ServerConfig(
                url="https://192.0.2.1",
                username="wtx2",
                password="364sdfoLdf"
            )]
    @property
    def server_url_list(self) -> List[str]:
        """获取服务器URL列表（兼容性）"""
        return [s.url for s in self.server_list]

settings = Settings()
