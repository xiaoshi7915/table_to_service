"""
PostgreSQL 数据源
用于监听术语库、SQL示例、自定义提示词等表的变更
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

from .base_source import BaseSource


class PostgreSQLSource(BaseSource):
    """PostgreSQL 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_string = config.get("connection_string")
        self.tables = config.get("tables", [])  # 要监听的表列表
        self.engine = None
        
        if not self.connection_string:
            raise ValueError("PostgreSQL 连接字符串未配置")
        
        try:
            self.engine = create_engine(self.connection_string)
        except Exception as e:
            logger.error(f"创建 PostgreSQL 连接失败: {e}")
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
        
        results = []
        tables_to_read = [table_name] if table_name else self.tables
        
        with self.engine.connect() as conn:
            for table in tables_to_read:
                try:
                    query = f"SELECT * FROM {table} WHERE is_deleted = false"
                    
                    if offset:
                        query += f" OFFSET {offset}"
                    if limit:
                        query += f" LIMIT {limit}"
                    
                    result = conn.execute(text(query))
                    rows = result.fetchall()
                    columns = result.keys()
                    
                    for row in rows:
                        record = dict(zip(columns, row))
                        record["_source_table"] = table  # 添加表名标识
                        results.append(record)
                    
                    logger.debug(f"从表 {table} 读取 {len(rows)} 条记录")
                except Exception as e:
                    logger.warning(f"读取表 {table} 失败: {e}")
                    continue
        
        return results
    
    def watch(self, callback) -> None:
        """
        监听数据变更（使用 PostgreSQL logical replication 或触发器）
        
        注意：这是一个简化实现，实际生产环境应该使用更可靠的CDC机制
        """
        # TODO: 实现 PostgreSQL logical replication 或触发器机制
        # 当前实现：定期轮询（作为临时方案）
        logger.warning("PostgreSQL CDC 监听未完全实现，当前使用轮询方式")
        
        # 这里应该实现真正的CDC监听
        # 可以使用：
        # 1. PostgreSQL logical replication
        # 2. pg_notify + 触发器
        # 3. Debezium（如果支持）
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        # 从数据源配置表中读取
        try:
            from app.core.database import LocalSessionLocal
            from app.models import DataSourceConfig
            
            db = LocalSessionLocal()
            try:
                # 查找对应的数据源配置
                source_config = db.query(DataSourceConfig).filter(
                    DataSourceConfig.name == self.name,
                    DataSourceConfig.is_deleted == False
                ).first()
                
                if source_config and source_config.last_sync_at:
                    return source_config.last_sync_at
                
                # 如果数据库中没有，尝试从配置中读取
                return self.config.get("last_sync_time")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"从数据库读取最后同步时间失败: {e}，使用配置中的值")
            return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        try:
            from app.core.database import LocalSessionLocal
            from app.models import DataSourceConfig
            
            db = LocalSessionLocal()
            try:
                # 更新数据源配置表中的最后同步时间
                source_config = db.query(DataSourceConfig).filter(
                    DataSourceConfig.name == self.name,
                    DataSourceConfig.is_deleted == False
                ).first()
                
                if source_config:
                    source_config.last_sync_at = sync_time
                    db.commit()
                    logger.debug(f"更新数据源配置表中的最后同步时间: {sync_time}")
                else:
                    # 如果配置不存在，更新内存中的配置
                    self.config["last_sync_time"] = sync_time
                    logger.debug(f"更新配置中的最后同步时间: {sync_time}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"更新数据库中的最后同步时间失败: {e}，更新配置中的值")
            self.config["last_sync_time"] = sync_time
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构"""
        if not self.engine:
            return {}
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_primary_key_column_names(table_name)
            
            return {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": col.get("default"),
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys,
            }
        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            return {}

