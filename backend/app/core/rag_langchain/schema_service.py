"""
数据库Schema服务
提取表结构、关联关系、样例数据等信息
"""
import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from loguru import logger

from app.models import DatabaseConfig
from app.core.db_factory import DatabaseConnectionFactory
from app.core.cache import get_cache_service
from app.core.performance_monitor import get_performance_monitor, track_time


class SchemaService:
    """数据库Schema服务"""
    
    def __init__(self, db_config: DatabaseConfig, enable_cache: bool = True, cache_ttl: int = 3600):
        """
        初始化Schema服务
        
        Args:
            db_config: 数据库配置
            enable_cache: 是否启用缓存
            cache_ttl: 缓存过期时间（秒），默认1小时
        """
        self.db_config = db_config
        self.db_type = db_config.db_type or "mysql"
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.cache_service = get_cache_service() if enable_cache else None
    
    def get_table_schema(
        self,
        table_names: Optional[List[str]] = None,
        include_sample_data: bool = True,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """
        获取表结构信息（包含字段、关联关系、样例数据）
        
        Args:
            table_names: 表名列表（如果为None，获取所有表）
            include_sample_data: 是否包含样例数据
            sample_rows: 样例数据行数
            
        Returns:
            Schema信息字典
        """
        start_time = time.time()
        
        # 检查缓存
        if self.enable_cache and self.cache_service:
            cache_key = self._generate_cache_key(table_names, include_sample_data, sample_rows)
            cached_result = self.cache_service.get(cache_key)
            if cached_result:
                elapsed_time = time.time() - start_time
                logger.info(f"从缓存获取Schema信息: {len(table_names or [])} 个表")
                get_performance_monitor().record_schema_load(elapsed_time, from_cache=True)
                return cached_result
            else:
                get_performance_monitor().record_cache_miss("schema")
        
        try:
            engine = DatabaseConnectionFactory.create_engine(self.db_config)
            inspector = inspect(engine)
            
            # 获取表列表
            if table_names is None:
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
            
            tables_info = []
            relationships = []
            
            for table_name in table_names:
                try:
                    # 获取表结构
                    table_info = self._get_table_info(inspector, table_name)
                    
                    # 获取样例数据
                    if include_sample_data:
                        table_info["sample_data"] = self._get_sample_data(
                            engine, table_name, sample_rows
                        )
                    
                    tables_info.append(table_info)
                    
                    # 获取外键关系
                    fk_relations = self._get_foreign_keys(inspector, table_name)
                    relationships.extend(fk_relations)
                    
                except Exception as e:
                    logger.warning(f"获取表 {table_name} 信息失败: {e}")
                    continue
            
            engine.dispose()
            
            elapsed_time = time.time() - start_time
            
            result = {
                "db_type": self.db_type,
                "database": self.db_config.database,
                "tables": tables_info,
                "relationships": relationships
            }
            
            # 记录性能指标
            get_performance_monitor().record_schema_load(elapsed_time, from_cache=False)
            
            # 缓存结果
            if self.enable_cache and self.cache_service:
                cache_key = self._generate_cache_key(table_names, include_sample_data, sample_rows)
                self.cache_service.set(cache_key, result, ttl=self.cache_ttl)
                logger.debug(f"已缓存Schema信息: {len(tables_info)} 个表")
            
            return result
            
        except Exception as e:
            logger.error(f"获取Schema信息失败: {e}", exc_info=True)
            return {
                "db_type": self.db_type,
                "database": self.db_config.database,
                "tables": [],
                "relationships": []
            }
    
    def _generate_cache_key(
        self,
        table_names: Optional[List[str]],
        include_sample_data: bool,
        sample_rows: int
    ) -> str:
        """
        生成Schema缓存键
        
        Args:
            table_names: 表名列表
            include_sample_data: 是否包含样例数据
            sample_rows: 样例数据行数
            
        Returns:
            缓存键字符串
        """
        key_data = {
            "db_config_id": self.db_config.id,
            "table_names": sorted(table_names) if table_names else None,
            "include_sample_data": include_sample_data,
            "sample_rows": sample_rows
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        return f"schema:{key_hash}"
    
    def clear_cache(self, table_names: Optional[List[str]] = None):
        """
        清除Schema缓存
        
        Args:
            table_names: 表名列表（如果为None，清除所有相关缓存）
        """
        if not self.cache_service:
            return
        
        if table_names:
            # 清除特定表的缓存
            cache_key = self._generate_cache_key(table_names, True, 5)
            self.cache_service.delete(cache_key)
            logger.info(f"已清除表 {table_names} 的Schema缓存")
        else:
            # 清除所有相关缓存（使用模式匹配）
            pattern = f"schema:*"
            count = self.cache_service.clear(pattern)
            logger.info(f"已清除 {count} 个Schema缓存项")
    
    def _get_table_info(self, inspector: Any, table_name: str) -> Dict[str, Any]:
        """
        获取单个表的详细信息
        
        Args:
            inspector: SQLAlchemy Inspector对象
            table_name: 表名
            
        Returns:
            表信息字典
        """
        # 获取列信息
        columns = inspector.get_columns(table_name)
        
        # 获取主键
        primary_keys = inspector.get_pk_constraint(table_name)
        pk_columns = primary_keys.get("constrained_columns", [])
        
        # 获取索引
        indexes = inspector.get_indexes(table_name)
        
        # 构建列信息列表
        column_list = []
        for col in columns:
            col_info = {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default", "")) if col.get("default") is not None else None,
                "primary_key": col["name"] in pk_columns,
                "comment": col.get("comment", "")
            }
            column_list.append(col_info)
        
        return {
            "name": table_name,
            "columns": column_list,
            "primary_keys": pk_columns,
            "indexes": [idx["name"] for idx in indexes]
        }
    
    def _get_foreign_keys(self, inspector: Any, table_name: str) -> List[Dict[str, Any]]:
        """
        获取外键关系
        
        Args:
            inspector: SQLAlchemy Inspector对象
            table_name: 表名
            
        Returns:
            外键关系列表
        """
        try:
            foreign_keys = inspector.get_foreign_keys(table_name)
            relations = []
            
            for fk in foreign_keys:
                relations.append({
                    "from_table": table_name,
                    "from_column": fk["constrained_columns"][0] if fk["constrained_columns"] else "",
                    "to_table": fk["referred_table"],
                    "to_column": fk["referred_columns"][0] if fk["referred_columns"] else "",
                    "name": fk.get("name", "")
                })
            
            return relations
        except Exception as e:
            logger.warning(f"获取表 {table_name} 外键关系失败: {e}")
            return []
    
    def _get_sample_data(
        self,
        engine: Any,
        table_name: str,
        rows: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取表的样例数据
        
        Args:
            engine: 数据库引擎
            table_name: 表名
            rows: 返回行数
            
        Returns:
            样例数据列表
        """
        try:
            with engine.connect() as conn:
                # 构建查询SQL（根据数据库类型）
                if self.db_type == "sqlserver":
                    sql = f"SELECT TOP {rows} * FROM {table_name}"
                elif self.db_type == "oracle":
                    sql = f"SELECT * FROM {table_name} WHERE ROWNUM <= {rows}"
                else:
                    sql = f"SELECT * FROM {table_name} LIMIT {rows}"
                
                result = conn.execute(text(sql))
                columns = result.keys()
                data = []
                
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # 处理特殊类型
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        elif value is None:
                            value = None
                        else:
                            value = str(value)
                        row_dict[col] = value
                    data.append(row_dict)
                
                return data
        except Exception as e:
            logger.warning(f"获取表 {table_name} 样例数据失败: {e}")
            return []


