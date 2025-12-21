"""
基础探查引擎
只探查表结构，不分析数据内容
"""
from typing import Dict, Any, Optional, List
from sqlalchemy import text, inspect
from loguru import logger

from .base_probe_engine import BaseProbeEngine
from .database_adapters import (
    MySQLAdapter, PostgreSQLAdapter, SQLServerAdapter, 
    OracleAdapter, SQLiteAdapter
)


class BasicProbeEngine(BaseProbeEngine):
    """基础探查引擎 - 只探查表结构"""
    
    def _get_adapter(self):
        """获取数据库适配器"""
        db_type = self.db_type.lower()
        adapters = {
            "mysql": MySQLAdapter,
            "postgresql": PostgreSQLAdapter,
            "sqlserver": SQLServerAdapter,
            "oracle": OracleAdapter,
            "sqlite": SQLiteAdapter,
        }
        adapter_class = adapters.get(db_type)
        if not adapter_class:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        return adapter_class()
    
    def probe_database(self) -> Dict[str, Any]:
        """
        库级探查（基础探查）
        只获取表数量、视图数量等元数据
        
        Returns:
            库级探查结果字典
        """
        adapter = self._get_adapter()
        database_name = self.db_config.database
        
        result = {
            "database_name": database_name,
            "db_type": self.db_type,
            "table_count": 0,
            "view_count": 0,
            "function_count": 0,
            "procedure_count": 0,
            "trigger_count": 0,
            "event_count": 0,
            "sequence_count": 0,
        }
        
        try:
            with self.engine.connect() as conn:
                # 获取对象数量
                if self.db_type == "sqlite":
                    queries = adapter.get_object_count_queries(database_name)
                    # SQLite特殊处理
                    for obj_type, query in queries.items():
                        try:
                            if obj_type == "tables":
                                row = conn.execute(text(query)).fetchone()
                                result["table_count"] = row[0] if row else 0
                            elif obj_type == "views":
                                row = conn.execute(text(query)).fetchone()
                                result["view_count"] = row[0] if row else 0
                            elif obj_type == "triggers":
                                row = conn.execute(text(query)).fetchone()
                                result["trigger_count"] = row[0] if row else 0
                        except Exception as e:
                            logger.warning(f"获取{obj_type}数量失败: {e}")
                elif self.db_type == "postgresql":
                    queries = adapter.get_object_count_queries(database_name, schema_name="public")
                    for obj_type, query in queries.items():
                        try:
                            row = conn.execute(text(query)).fetchone()
                            count = row[0] if row else 0
                            if obj_type == "tables":
                                result["table_count"] = count
                            elif obj_type == "views":
                                result["view_count"] = count
                            elif obj_type == "functions":
                                result["function_count"] = count
                            elif obj_type == "procedures":
                                result["procedure_count"] = count
                            elif obj_type == "triggers":
                                result["trigger_count"] = count
                            elif obj_type == "sequences":
                                result["sequence_count"] = count
                        except Exception as e:
                            logger.warning(f"获取{obj_type}数量失败: {e}")
                else:
                    # MySQL, SQL Server, Oracle
                    queries = adapter.get_object_count_queries(database_name)
                    for obj_type, query in queries.items():
                        try:
                            row = conn.execute(text(query)).fetchone()
                            count = row[0] if row else 0
                            if obj_type == "tables":
                                result["table_count"] = count
                            elif obj_type == "views":
                                result["view_count"] = count
                            elif obj_type == "functions":
                                result["function_count"] = count
                            elif obj_type == "procedures":
                                result["procedure_count"] = count
                            elif obj_type == "triggers":
                                result["trigger_count"] = count
                            elif obj_type == "events":
                                result["event_count"] = count
                            elif obj_type == "sequences":
                                result["sequence_count"] = count
                        except Exception as e:
                            logger.warning(f"获取{obj_type}数量失败: {e}")
        
        except Exception as e:
            logger.error(f"库级探查失败: {e}", exc_info=True)
            raise
        
        return result
    
    def probe_table(self, table_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        表级探查（基础探查）
        获取字段信息、主键、索引、约束、行数、表注释
        
        Args:
            table_name: 表名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            表级探查结果字典
        """
        adapter = self._get_adapter()
        database_name = self.db_config.database
        
        result = {
            "database_name": database_name,
            "table_name": table_name,
            "schema_name": schema_name,
            "column_count": 0,
            "row_count": None,
            "table_comment": None,
            "primary_key": [],
            "indexes": [],
            "foreign_keys": [],
            "constraints": [],
            "columns": [],
        }
        
        try:
            inspector = inspect(self.engine)
            
            # 获取表统计信息和注释
            try:
                with self.engine.connect() as conn:
                    if self.db_type == "mysql":
                        # MySQL: 获取表行数和表注释
                        table_info_query = text("""
                            SELECT 
                                table_rows,
                                table_comment
                            FROM information_schema.tables
                            WHERE table_schema = :db_name AND table_name = :table_name
                        """)
                        table_info_result = conn.execute(
                            table_info_query,
                            {"db_name": database_name, "table_name": table_name}
                        ).fetchone()
                        if table_info_result:
                            result["row_count"] = int(table_info_result[0]) if table_info_result[0] else None
                            result["table_comment"] = table_info_result[1] if table_info_result[1] else None
                    elif self.db_type == "postgresql":
                        # PostgreSQL: 获取表注释
                        comment_query = text("""
                            SELECT obj_description(
                                (SELECT oid FROM pg_class WHERE relname = :table_name 
                                 AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = COALESCE(:schema_name, 'public'))),
                                'pg_class'
                            ) AS table_comment
                        """)
                        comment_result = conn.execute(
                            comment_query,
                            {"table_name": table_name, "schema_name": schema_name or "public"}
                        ).fetchone()
                        if comment_result and comment_result[0]:
                            result["table_comment"] = comment_result[0]
                        # PostgreSQL: 获取表行数（估算值）
                        row_count_query = text(f"""
                            SELECT reltuples::bigint AS row_count
                            FROM pg_class
                            WHERE relname = :table_name
                            AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = COALESCE(:schema_name, 'public'))
                        """)
                        row_count_result = conn.execute(
                            row_count_query,
                            {"table_name": table_name, "schema_name": schema_name or "public"}
                        ).fetchone()
                        if row_count_result and row_count_result[0]:
                            result["row_count"] = int(row_count_result[0])
            except Exception as e:
                logger.warning(f"获取表统计信息或注释失败: {e}")
            
            # 获取列信息
            if self.db_type == "sqlite":
                # SQLite特殊处理
                with self.engine.connect() as conn:
                    pragma_result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns_info = []
                    primary_keys = []
                    
                    for row in pragma_result:
                        col_name = row[1]
                        col_type = row[2]
                        notnull = row[3]
                        dflt_value = row[4]
                        pk = row[5]
                        
                        if pk:
                            primary_keys.append(col_name)
                        
                        columns_info.append({
                            "name": col_name,
                            "type": col_type,
                            "nullable": notnull == 0,
                            "default": str(dflt_value) if dflt_value is not None else None,
                            "primary_key": pk == 1,
                        })
                    
                    result["columns"] = columns_info
                    result["column_count"] = len(columns_info)
                    result["primary_key"] = primary_keys
            else:
                # 使用SQLAlchemy inspect
                columns = inspector.get_columns(table_name, schema=schema_name)
                result["column_count"] = len(columns)
                
                # 转换列信息
                for col in columns:
                    col_info = {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": str(col.get("default", "")) if col.get("default") is not None else None,
                        "autoincrement": col.get("autoincrement", False),
                    }
                    result["columns"].append(col_info)
                
                # 获取主键
                try:
                    pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
                    if pk_constraint:
                        result["primary_key"] = pk_constraint.get("constrained_columns", [])
                except Exception as e:
                    logger.warning(f"获取主键失败: {e}")
                
                # 获取索引
                try:
                    indexes = inspector.get_indexes(table_name, schema=schema_name)
                    result["indexes"] = [
                        {
                            "name": idx.get("name", ""),
                            "columns": idx.get("column_names", []),
                            "unique": idx.get("unique", False),
                        }
                        for idx in indexes
                    ]
                except Exception as e:
                    logger.warning(f"获取索引失败: {e}")
                
                # 获取外键
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name, schema=schema_name)
                    result["foreign_keys"] = [
                        {
                            "name": fk.get("name", ""),
                            "constrained_columns": fk.get("constrained_columns", []),
                            "referred_table": fk.get("referred_table", ""),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                        for fk in foreign_keys
                    ]
                except Exception as e:
                    logger.warning(f"获取外键失败: {e}")
        
        except Exception as e:
            logger.error(f"表级探查失败: {e}", exc_info=True)
            raise
        
        return result
    
    def probe_column(
        self, 
        table_name: str, 
        column_name: str, 
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        列级探查（基础探查）
        获取字段类型、是否可空、默认值、注释
        
        Args:
            table_name: 表名
            column_name: 字段名
            schema_name: Schema名（PostgreSQL等需要）
            
        Returns:
            列级探查结果字典
        """
        adapter = self._get_adapter()
        database_name = self.db_config.database
        
        result = {
            "database_name": database_name,
            "table_name": table_name,
            "column_name": column_name,
            "schema_name": schema_name,
            "data_type": "",
            "nullable": True,
            "default_value": None,
            "comment": "",
        }
        
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name, schema=schema_name)
            
            # 查找指定字段
            for col in columns:
                if col["name"] == column_name:
                    result["data_type"] = str(col["type"])
                    result["nullable"] = col.get("nullable", True)
                    result["default_value"] = str(col.get("default", "")) if col.get("default") is not None else None
                    
                    # 获取注释（根据数据库类型）
                    if self.db_type == "mysql":
                        try:
                            with self.engine.connect() as conn:
                                comment_query = text("""
                                    SELECT COLUMN_COMMENT 
                                    FROM INFORMATION_SCHEMA.COLUMNS 
                                    WHERE TABLE_SCHEMA = :db_name 
                                    AND TABLE_NAME = :table_name
                                    AND COLUMN_NAME = :column_name
                                """)
                                comment_result = conn.execute(
                                    comment_query, 
                                    {
                                        "db_name": database_name,
                                        "table_name": table_name,
                                        "column_name": column_name
                                    }
                                )
                                row = comment_result.fetchone()
                                if row and row[0]:
                                    result["comment"] = row[0]
                        except Exception as e:
                            logger.warning(f"获取MySQL字段注释失败: {e}")
                    elif self.db_type == "postgresql":
                        try:
                            with self.engine.connect() as conn:
                                comment_query = text("""
                                    SELECT d.description
                                    FROM pg_attribute a
                                    JOIN pg_class c ON a.attrelid = c.oid
                                    JOIN pg_namespace n ON c.relnamespace = n.oid
                                    LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
                                    WHERE c.relname = :table_name 
                                    AND n.nspname = COALESCE(:schema_name, 'public')
                                    AND a.attname = :column_name
                                    AND a.attnum > 0
                                    AND NOT a.attisdropped
                                """)
                                comment_result = conn.execute(
                                    comment_query,
                                    {
                                        "table_name": table_name,
                                        "schema_name": schema_name or "public",
                                        "column_name": column_name
                                    }
                                )
                                row = comment_result.fetchone()
                                if row and row[0]:
                                    result["comment"] = row[0]
                        except Exception as e:
                            logger.warning(f"获取PostgreSQL字段注释失败: {e}")
                    
                    break
        
        except Exception as e:
            logger.error(f"列级探查失败: {e}", exc_info=True)
            raise
        
        return result

