"""
CocoIndex 配置模块
"""
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from app.core.config import settings


class CocoIndexConfig:
    """CocoIndex 配置类"""
    
    # PostgreSQL 连接配置（使用现有的本地数据库）
    POSTGRESQL_CONNECTION_STRING: str = settings.local_database_url
    
    # 文档存储配置
    DOCUMENT_STORAGE_TYPE: str = os.getenv("DOCUMENT_STORAGE_TYPE", "local")  # local, s3, azure, gdrive
    DOCUMENT_STORAGE_PATH: str = os.getenv("DOCUMENT_STORAGE_PATH", str(Path(__file__).parent.parent.parent.parent / "storage" / "documents"))
    DOCUMENT_TEMP_PATH: str = os.getenv("DOCUMENT_TEMP_PATH", str(Path(__file__).parent.parent.parent.parent / "storage" / "temp"))
    
    # 向量配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-base-zh-v1.5")  # 中文嵌入模型
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # 向量维度
    
    # 文档处理配置
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 最大文件大小（MB转字节，默认100MB）
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))  # 文档分块大小（tokens）
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))  # 分块重叠大小（tokens）
    
    # 同步配置
    SYNC_ENABLED: bool = os.getenv("SYNC_ENABLED", "true").lower() == "true"
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "60"))  # 默认同步间隔（秒）
    CDC_ENABLED: bool = os.getenv("CDC_ENABLED", "true").lower() == "true"  # Change Data Capture
    
    # 索引配置
    INDEX_COLLECTIONS = {
        "knowledge": "knowledge",  # 业务知识库
        "terminologies": "terminologies",  # 术语库
        "sql_examples": "sql_examples",  # SQL示例
        "documents": "documents",  # 文档
        "schemas": "schemas",  # 数据库Schema
    }
    
    # 数据源配置
    SUPPORTED_SOURCE_TYPES = [
        "postgresql",  # PostgreSQL数据库
        "mysql",  # MySQL数据库
        "sqlserver",  # SQL Server数据库
        "oracle",  # Oracle数据库
        "mongodb",  # MongoDB数据库
        "s3",  # AWS S3
        "azure_blob",  # Azure Blob Storage
        "google_drive",  # Google Drive
        "rest_api",  # REST API
        "graphql",  # GraphQL API
        "file",  # 本地文件
    ]
    
    @classmethod
    def get_document_storage_path(cls) -> Path:
        """获取文档存储路径"""
        path = Path(cls.DOCUMENT_STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def get_document_temp_path(cls) -> Path:
        """获取文档临时路径"""
        path = Path(cls.DOCUMENT_TEMP_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置"""
        try:
            # 检查 PostgreSQL 连接字符串
            if not cls.POSTGRESQL_CONNECTION_STRING:
                logger.error("CocoIndex: PostgreSQL 连接字符串未配置")
                return False
            
            # 检查文档存储路径
            storage_path = cls.get_document_storage_path()
            if not storage_path.exists():
                logger.warning(f"CocoIndex: 文档存储路径不存在，已创建: {storage_path}")
            
            temp_path = cls.get_document_temp_path()
            if not temp_path.exists():
                logger.warning(f"CocoIndex: 文档临时路径不存在，已创建: {temp_path}")
            
            logger.info("CocoIndex 配置验证通过")
            return True
        except Exception as e:
            logger.error(f"CocoIndex 配置验证失败: {e}")
            return False


# 全局配置实例
cocoindex_config = CocoIndexConfig()

# 初始化时验证配置
if __name__ != "__main__":
    cocoindex_config.validate_config()

