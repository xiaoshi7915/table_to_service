"""
数据库 Schema 数据源
用于同步关系型数据库的表结构信息
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import create_engine, inspect, text

from .base_source import BaseSource
from app.core.db_factory import DatabaseConnectionFactory


class DatabaseSchemaSource(BaseSource):
    """数据库 Schema 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_config_id = config.get("db_config_id")  # 关联的数据库配置ID
        self.db_factory = DatabaseConnectionFactory()
    
    def read(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        table_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        读取数据库 Schema 信息
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            table_names: 可选，指定要读取的表名列表
            
        Returns:
            Schema 信息列表
        """
        if not self.db_config_id:
            logger.warning("数据库配置ID未指定")
            return []
        
        try:
            # 获取数据库连接
            db_engine = self.db_factory.get_engine(self.db_config_id)
            if not db_engine:
                logger.error(f"无法获取数据库连接: {self.db_config_id}")
                return []
            
            inspector = inspect(db_engine)
            schema_info = []
            
            # 获取所有表名
            all_tables = inspector.get_table_names()
            if table_names:
                all_tables = [t for t in all_tables if t in table_names]
            
            # 分页
            if offset:
                all_tables = all_tables[offset:]
            if limit:
                all_tables = all_tables[:limit]
            
            # 获取每个表的结构
            for table_name in all_tables:
                try:
                    columns = inspector.get_columns(table_name)
                    primary_keys = inspector.get_primary_key_column_names(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)
                    
                    table_info = {
                        "table_name": table_name,
                        "schema": inspector.default_schema_name,
                        "columns": [
                            {
                                "name": col["name"],
                                "type": str(col["type"]),
                                "nullable": col.get("nullable", True),
                                "default": str(col.get("default")) if col.get("default") is not None else None,
                                "comment": col.get("comment"),
                            }
                            for col in columns
                        ],
                        "primary_keys": primary_keys,
                        "foreign_keys": [
                            {
                                "name": fk["name"],
                                "constrained_columns": fk["constrained_columns"],
                                "referred_table": fk["referred_table"],
                                "referred_columns": fk["referred_columns"],
                            }
                            for fk in foreign_keys
                        ],
                        "indexes": [
                            {
                                "name": idx["name"],
                                "columns": idx["column_names"],
                                "unique": idx.get("unique", False),
                            }
                            for idx in indexes
                        ],
                        "_source_type": "database_schema",
                        "_db_config_id": self.db_config_id,
                    }
                    
                    schema_info.append(table_info)
                except Exception as e:
                    logger.warning(f"获取表 {table_name} 结构失败: {e}")
                    continue
            
            return schema_info
        except Exception as e:
            logger.error(f"读取数据库 Schema 失败: {e}")
            return []
    
    def watch(self, callback) -> None:
        """
        监听 Schema 变更
        
        注意：数据库 Schema 变更监听比较复杂，通常使用定时同步
        """
        logger.warning("数据库 Schema 变更监听未实现，建议使用定时同步")
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")

