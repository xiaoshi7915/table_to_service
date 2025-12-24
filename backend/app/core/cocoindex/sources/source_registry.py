"""
数据源注册表
统一管理所有数据源
"""
from typing import Dict, Optional, List
from loguru import logger

from .base_source import BaseSource
from .postgresql_source import PostgreSQLSource
from .mysql_source import MySQLSource
from .file_source import FileSource
from .database_schema_source import DatabaseSchemaSource
from .mongodb_source import MongoDBSource
from .s3_source import S3Source
from .azure_blob_source import AzureBlobSource
from .google_drive_source import GoogleDriveSource
from .api_source import APISource


class SourceRegistry:
    """数据源注册表"""
    
    def __init__(self):
        self._sources: Dict[str, BaseSource] = {}
        self._source_types = {
            "postgresql": PostgreSQLSource,
            "mysql": MySQLSource,
            "file": FileSource,
            "database_schema": DatabaseSchemaSource,
            "mongodb": MongoDBSource,
            "s3": S3Source,
            "azure_blob": AzureBlobSource,
            "google_drive": GoogleDriveSource,
            "rest_api": APISource,
            "graphql": APISource,
        }
    
    def register_source(self, source: BaseSource) -> None:
        """
        注册数据源
        
        Args:
            source: 数据源实例
        """
        source_info = source.get_source_info()
        source_key = f"{source_info['source_type']}:{source_info['name']}"
        self._sources[source_key] = source
        logger.info(f"注册数据源: {source_key}")
    
    def get_source(self, source_type: str, name: str) -> Optional[BaseSource]:
        """
        获取数据源
        
        Args:
            source_type: 数据源类型
            name: 数据源名称
            
        Returns:
            数据源实例，如果不存在则返回 None
        """
        source_key = f"{source_type}:{name}"
        return self._sources.get(source_key)
    
    def list_sources(self, source_type: Optional[str] = None) -> List[BaseSource]:
        """
        列出所有数据源
        
        Args:
            source_type: 可选，过滤特定类型的数据源
            
        Returns:
            数据源列表
        """
        if source_type:
            return [
                source for key, source in self._sources.items()
                if key.startswith(f"{source_type}:")
            ]
        return list(self._sources.values())
    
    def create_source(self, config: Dict) -> BaseSource:
        """
        创建数据源实例
        
        Args:
            config: 数据源配置
            
        Returns:
            数据源实例
            
        Raises:
            ValueError: 如果不支持该数据源类型
        """
        source_type = config.get("source_type")
        if source_type not in self._source_types:
            raise ValueError(f"不支持的数据源类型: {source_type}")
        
        source_class = self._source_types[source_type]
        return source_class(config)
    
    def register_from_config(self, config: Dict) -> BaseSource:
        """
        从配置创建并注册数据源
        
        Args:
            config: 数据源配置
            
        Returns:
            数据源实例
        """
        source = self.create_source(config)
        self.register_source(source)
        return source


# 全局注册表实例
source_registry = SourceRegistry()

