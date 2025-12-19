"""
数据库Schema加载服务
从数据库配置中加载表结构和字段信息
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from loguru import logger

from app.models import DatabaseConfig
from app.core.db_factory import DatabaseConnectionFactory
from app.core.sql_dialect import SQLDialectFactory


class SchemaLoader:
    """数据库Schema加载器"""
    
    def __init__(self, db_config: DatabaseConfig):
        """
        初始化加载器
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self.db_type = db_config.db_type or "mysql"
    
    def load_schema(
        self,
        table_names: Optional[List[str]] = None,
        include_comments: bool = True
    ) -> Dict[str, Any]:
        """
        加载数据库schema信息
        
        Args:
            table_names: 要加载的表名列表（None表示加载所有表）
            include_comments: 是否包含字段注释
            
        Returns:
            schema信息，格式：{
                "tables": [
                    {
                        "name": "表名",
                        "columns": [
                            {
                                "name": "字段名",
                                "type": "数据类型",
                                "nullable": True/False,
                                "default": "默认值",
                                "primary_key": True/False,
                                "comment": "字段注释"
                            }
                        ]
                    }
                ]
            }
        """
        try:
            # 创建数据库连接
            engine = DatabaseConnectionFactory.create_engine(self.db_config)
            
            # 使用SQLAlchemy的inspect获取schema信息
            inspector = inspect(engine)
            
            # 获取表列表
            if table_names is None:
                if self.db_type == "sqlite":
                    # SQLite特殊处理
                    with engine.connect() as conn:
                        result = conn.execute(text(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                        ))
                        table_names = [row[0] for row in result]
                elif self.db_type == "postgresql":
                    table_names = inspector.get_table_names(schema='public')
                else:
                    table_names = inspector.get_table_names()
            
            tables = []
            for table_name in table_names:
                try:
                    table_info = self._load_table_info(
                        inspector, 
                        table_name, 
                        include_comments
                    )
                    if table_info:
                        tables.append(table_info)
                except Exception as e:
                    logger.warning(f"加载表 {table_name} 的信息失败: {e}")
                    continue
            
            engine.dispose()
            
            return {
                "db_type": self.db_type,
                "database": self.db_config.database,
                "tables": tables
            }
            
        except Exception as e:
            logger.error(f"加载数据库schema失败: {e}", exc_info=True)
            return {
                "db_type": self.db_type,
                "database": self.db_config.database,
                "tables": []
            }
    
    def _load_table_info(
        self,
        inspector: Any,
        table_name: str,
        include_comments: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        加载单个表的信息
        
        Args:
            inspector: SQLAlchemy Inspector对象
            table_name: 表名
            include_comments: 是否包含注释
            
        Returns:
            表信息字典
        """
        try:
            # 获取列信息
            columns = inspector.get_columns(table_name)
            
            # 获取主键
            primary_keys = inspector.get_pk_constraint(table_name)
            pk_columns = primary_keys.get("constrained_columns", [])
            
            # 构建列信息列表
            column_list = []
            for col in columns:
                col_info = {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default", "")) if col.get("default") is not None else None,
                    "primary_key": col["name"] in pk_columns,
                    "comment": col.get("comment", "") if include_comments else ""
                }
                column_list.append(col_info)
            
            return {
                "name": table_name,
                "columns": column_list
            }
            
        except Exception as e:
            logger.error(f"加载表 {table_name} 信息失败: {e}")
            return None
    
    def load_table_names(self) -> List[str]:
        """
        加载所有表名
        
        Returns:
            表名列表
        """
        try:
            engine = DatabaseConnectionFactory.create_engine(self.db_config)
            inspector = inspect(engine)
            
            if self.db_type == "sqlite":
                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ))
                    table_names = [row[0] for row in result]
            elif self.db_type == "postgresql":
                table_names = inspector.get_table_names(schema='public')
            else:
                table_names = inspector.get_table_names()
            
            engine.dispose()
            return table_names
            
        except Exception as e:
            logger.error(f"加载表名列表失败: {e}", exc_info=True)
            return []


