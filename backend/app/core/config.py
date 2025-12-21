"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
from loguru import logger

# 获取backend目录的路径
BACKEND_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# 加载环境变量（优先从backend目录，如果不存在则从项目根目录）
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # 尝试从项目根目录加载
    root_env = BACKEND_DIR.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    
    # 目标数据库配置（用于表转服务的目标数据库）
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "test_db")
    
    # 本地数据库配置（用于服务自身数据存储：用户表等）
    LOCAL_DB_TYPE: str = os.getenv("LOCAL_DB_TYPE", "mysql").lower()  # 支持 mysql 或 postgresql
    LOCAL_DB_HOST: str = os.getenv("LOCAL_DB_HOST", "localhost")
    LOCAL_DB_PORT: int = int(os.getenv("LOCAL_DB_PORT", "3306"))
    LOCAL_DB_USER: str = os.getenv("LOCAL_DB_USER", "root")
    LOCAL_DB_PASSWORD: str = os.getenv("LOCAL_DB_PASSWORD", "")
    LOCAL_DB_NAME: str = os.getenv("LOCAL_DB_NAME", "local_service_db")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # 服务配置
    HOST: str = os.getenv("API_HOST") or os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("API_PORT") or os.getenv("PORT", "5001"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS配置
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000")
    
    # API服务地址配置（用于生成接口文档中的完整URL）
    API_SERVER_HOST: str = os.getenv("API_SERVER_HOST", "")  # 如果为空，则从请求头获取
    API_SERVER_PORT: int = int(os.getenv("API_SERVER_PORT", "8300"))  # API服务端口
    API_SERVER_SCHEME: str = os.getenv("API_SERVER_SCHEME", "http")  # http 或 https
    
    # Redis配置（用于缓存）
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")  # Redis连接URL
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")  # Redis密码（可选）
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))  # Redis数据库编号（默认0）
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 缓存过期时间（秒，默认1小时）
    
    # 数据库连接池配置（可选，用于优化性能）
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))  # 连接池大小（默认10）
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))  # 最大溢出连接数（默认20）
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 连接回收时间（秒，默认1小时）
    LOCAL_DB_POOL_SIZE: int = int(os.getenv("LOCAL_DB_POOL_SIZE", "5"))  # 本地数据库连接池大小（默认5）
    LOCAL_DB_MAX_OVERFLOW: int = int(os.getenv("LOCAL_DB_MAX_OVERFLOW", "10"))  # 本地数据库最大溢出连接数（默认10）
    
    @property
    def database_url(self) -> str:
        """生成目标数据库连接URL（用于表转服务）"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    @property
    def local_database_url(self) -> str:
        """生成本地数据库连接URL（用于服务自身数据存储）"""
        db_type = self.LOCAL_DB_TYPE.lower()
        
        # 清理 hostname（去除首尾空格）
        clean_host = self.LOCAL_DB_HOST.strip() if self.LOCAL_DB_HOST else ""
        
        # 编码用户名和密码中的特殊字符
        encoded_user = quote_plus(self.LOCAL_DB_USER)
        encoded_password = quote_plus(self.LOCAL_DB_PASSWORD)
        
        if db_type == "postgresql":
            # PostgreSQL: postgresql+psycopg2://user:pass@host:port/db
            return f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{clean_host}:{self.LOCAL_DB_PORT}/{self.LOCAL_DB_NAME}"
        elif db_type == "mysql":
            # MySQL: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
            return f"mysql+pymysql://{encoded_user}:{encoded_password}@{clean_host}:{self.LOCAL_DB_PORT}/{self.LOCAL_DB_NAME}?charset=utf8mb4"
        else:
            raise ValueError(f"不支持的本地数据库类型: {db_type}，支持的类型: mysql, postgresql")
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """获取允许的源列表"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 允许额外的环境变量


# 全局配置实例
settings = Settings()

# 检查SECRET_KEY是否为默认值（生产环境安全警告）
if settings.SECRET_KEY == "your-secret-key-change-this-in-production":
    if not settings.DEBUG:
        # 生产环境：记录ERROR并建议停止服务
        logger.error("=" * 60)
        logger.error("⚠️  严重安全警告：SECRET_KEY使用默认值！")
        logger.error("生产环境必须修改SECRET_KEY，否则存在严重安全风险！")
        logger.error("请在.env文件中设置一个强随机字符串作为SECRET_KEY")
        logger.error("=" * 60)
        # 注意：这里不阻止启动，但记录严重警告
    else:
        # 开发环境：使用warnings
        import warnings
        warnings.warn(
            "⚠️  安全警告：SECRET_KEY使用默认值，生产环境请务必修改！",
            UserWarning
        )

