"""
探查引擎基类
定义探查引擎的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from sqlalchemy import Engine
from app.models import DatabaseConfig
from loguru import logger


class BaseProbeEngine(ABC):
    """探查引擎基类"""
    
    def __init__(self, db_config: DatabaseConfig, engine: Optional[Engine] = None):
        """
        初始化探查引擎
        
        Args:
            db_config: 数据库配置对象
            engine: SQLAlchemy引擎对象（可选，如果不提供则从db_config创建）
        """
        self.db_config = db_config
        self.engine = engine
        self.db_type = (db_config.db_type or "mysql").lower()
    
    def connect(self) -> Engine:
        """
        建立数据库连接
        
        Returns:
            SQLAlchemy引擎对象
        """
        if self.engine is None:
            from app.core.db_factory import DatabaseConnectionFactory
            self.engine = DatabaseConnectionFactory.create_engine(self.db_config)
        return self.engine
    
    def disconnect(self):
        """断开数据库连接"""
        if self.engine:
            try:
                self.engine.dispose()
            except Exception as e:
                logger.warning(f"断开数据库连接时出错: {e}")
            finally:
                self.engine = None
    
    @abstractmethod
    def probe_database(self) -> Dict[str, Any]:
        """
        库级探查（抽象方法）
        
        Returns:
            库级探查结果字典
        """
        pass
    
    @abstractmethod
    def probe_table(self, table_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        表级探查（抽象方法）
        
        Args:
            table_name: 表名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            表级探查结果字典
        """
        pass
    
    @abstractmethod
    def probe_column(
        self, 
        table_name: str, 
        column_name: str, 
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        列级探查（抽象方法）
        
        Args:
            table_name: 表名
            column_name: 字段名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            列级探查结果字典
        """
        pass
    
    def get_adapter(self):
        """
        获取数据库适配器
        
        Returns:
            数据库适配器对象
        """
        from app.core.sql_dialect import SQLDialectFactory
        return SQLDialectFactory.get_adapter(self.db_type)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

