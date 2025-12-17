"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv

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
    
    @property
    def database_url(self) -> str:
        """生成目标数据库连接URL（用于表转服务）"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    @property
    def local_database_url(self) -> str:
        """生成本地数据库连接URL（用于服务自身数据存储）"""
        return f"mysql+pymysql://{self.LOCAL_DB_USER}:{self.LOCAL_DB_PASSWORD}@{self.LOCAL_DB_HOST}:{self.LOCAL_DB_PORT}/{self.LOCAL_DB_NAME}?charset=utf8mb4"
    
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
    import warnings
    warnings.warn(
        "⚠️  安全警告：SECRET_KEY使用默认值，生产环境请务必修改！",
        UserWarning
    )

