"""
MySQL 数据源
用于监听MySQL数据库表的变更
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import create_engine, text, inspect

from .base_source import BaseSource


class MySQLSource(BaseSource):
    """MySQL 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_string = config.get("connection_string")
        self.tables = config.get("tables", [])  # 要监听的表列表
        self.engine = None
        
        if not self.connection_string:
            raise ValueError("MySQL 连接字符串未配置")
        
        try:
            self.engine = create_engine(self.connection_string)
        except Exception as e:
            logger.error(f"创建 MySQL 连接失败: {e}")
            raise
    
    def read(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        table_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        读取数据
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            table_name: 表名（如果指定，只读取该表）
            
        Returns:
            数据记录列表
        """
        if not self.engine:
            return []
        
        try:
            tables_to_read = [table_name] if table_name else (self.tables or [])
            if not tables_to_read:
                # 如果没有指定表，返回空列表
                return []
            
            all_records = []
            with self.engine.connect() as conn:
                for table in tables_to_read:
                    query = f"SELECT * FROM {table}"
                    if limit:
                        query += f" LIMIT {limit}"
                    if offset:
                        query += f" OFFSET {offset}"
                    
                    result = conn.execute(text(query))
                    for row in result:
                        record = dict(row._mapping)
                        record['_source_table'] = table
                        all_records.append(record)
            
            return all_records
        except Exception as e:
            logger.error(f"读取 MySQL 数据失败: {e}")
            return []
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        return {
            "source_type": "mysql",
            "name": self.name,
            "connection_string": self.connection_string[:50] + "..." if len(self.connection_string) > 50 else self.connection_string,
            "tables": self.tables
        }

