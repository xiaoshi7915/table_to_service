"""
SQL方言适配器
处理不同数据库的SQL语法差异，如标识符转义、分页语法等
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger


class SQLDialectAdapter(ABC):
    """SQL方言适配器基类"""
    
    @abstractmethod
    def escape_identifier(self, identifier: str) -> str:
        """
        转义SQL标识符（表名、字段名等）
        
        Args:
            identifier: 标识符名称
            
        Returns:
            转义后的标识符
        """
        pass
    
    @abstractmethod
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """
        构建分页子句
        
        Args:
            limit: 限制返回行数
            offset: 偏移量
            
        Returns:
            分页SQL子句
        """
        pass
    
    @abstractmethod
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """
        获取表列表的SQL查询
        
        Args:
            schema: 数据库模式名（可选）
            
        Returns:
            SQL查询语句
        """
        pass
    
    @abstractmethod
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """
        获取表信息的SQL查询（字段、主键等）
        
        Args:
            table_name: 表名
            schema: 数据库模式名（可选）
            
        Returns:
            SQL查询语句
        """
        pass
    
    def normalize_sql(self, sql: str) -> str:
        """
        标准化SQL语句（可选，用于处理一些通用差异）
        
        Args:
            sql: 原始SQL语句
            
        Returns:
            标准化后的SQL语句
        """
        return sql


class MySQLAdapter(SQLDialectAdapter):
    """MySQL方言适配器"""
    
    def escape_identifier(self, identifier: str) -> str:
        """MySQL使用反引号转义标识符"""
        if not identifier:
            return identifier
        # 如果已经包含反引号，直接返回
        if identifier.startswith("`") and identifier.endswith("`"):
            return identifier
        return f"`{identifier}`"
    
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """MySQL: LIMIT n OFFSET m"""
        if limit is None:
            return ""
        if offset is None or offset == 0:
            return f"LIMIT {limit}"
        return f"LIMIT {limit} OFFSET {offset}"
    
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """MySQL: 从information_schema获取表列表"""
        if schema:
            return f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"
        return "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()"
    
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """MySQL: 从information_schema获取表信息"""
        schema_clause = f"AND table_schema = '{schema}'" if schema else "AND table_schema = DATABASE()"
        return f"""
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                IS_NULLABLE, 
                COLUMN_DEFAULT, 
                COLUMN_KEY,
                COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}' {schema_clause}
            ORDER BY ORDINAL_POSITION
        """


class PostgreSQLAdapter(SQLDialectAdapter):
    """PostgreSQL方言适配器"""
    
    def escape_identifier(self, identifier: str) -> str:
        """PostgreSQL使用双引号转义标识符"""
        if not identifier:
            return identifier
        if identifier.startswith('"') and identifier.endswith('"'):
            return identifier
        return f'"{identifier}"'
    
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """PostgreSQL: LIMIT n OFFSET m"""
        if limit is None:
            return ""
        if offset is None or offset == 0:
            return f"LIMIT {limit}"
        return f"LIMIT {limit} OFFSET {offset}"
    
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """PostgreSQL: 从information_schema获取表列表"""
        schema_name = schema or 'public'
        # 排除系统schema和视图，只返回用户表
        # 使用单引号转义防止SQL注入
        schema_name_escaped = schema_name.replace("'", "''")
        return f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema_name_escaped}'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
    
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """PostgreSQL: 从information_schema获取表信息"""
        schema_clause = f"AND table_schema = '{schema}'" if schema else "AND table_schema = 'public'"
        return f"""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN 'PRI' ELSE '' END as column_key,
                '' as column_comment
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = '{table_name}'
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = '{table_name}' {schema_clause}
            ORDER BY c.ordinal_position
        """


class SQLiteAdapter(SQLDialectAdapter):
    """SQLite方言适配器"""
    
    def escape_identifier(self, identifier: str) -> str:
        """SQLite可以使用方括号或反引号转义标识符"""
        if not identifier:
            return identifier
        if (identifier.startswith("[") and identifier.endswith("]")) or \
           (identifier.startswith("`") and identifier.endswith("`")):
            return identifier
        return f'"{identifier}"'
    
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """SQLite: LIMIT n OFFSET m"""
        if limit is None:
            return ""
        if offset is None or offset == 0:
            return f"LIMIT {limit}"
        return f"LIMIT {limit} OFFSET {offset}"
    
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """SQLite: 从sqlite_master获取表列表"""
        return "SELECT name as table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """SQLite: 使用PRAGMA table_info获取表信息"""
        # SQLite不支持在SQL查询中使用PRAGMA，需要在应用层处理
        # 这里返回一个占位查询，实际应该使用PRAGMA table_info(table_name)
        # 注意：SQLite的PRAGMA需要在应用层单独处理
        return f"PRAGMA table_info({self.escape_identifier(table_name)})"


class SQLServerAdapter(SQLDialectAdapter):
    """SQL Server方言适配器"""
    
    def escape_identifier(self, identifier: str) -> str:
        """SQL Server使用方括号转义标识符"""
        if not identifier:
            return identifier
        if identifier.startswith("[") and identifier.endswith("]"):
            return identifier
        return f"[{identifier}]"
    
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """SQL Server: OFFSET m ROWS FETCH NEXT n ROWS ONLY"""
        if limit is None:
            return ""
        if offset is None or offset == 0:
            # SQL Server 2012+ 支持 FETCH NEXT
            return f"OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
    
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """SQL Server: 从sys.tables获取表列表"""
        if schema:
            schema_escaped = schema.replace("'", "''")  # 防止SQL注入
            return f"SELECT name as table_name FROM sys.tables WHERE schema_id = SCHEMA_ID('{schema_escaped}') ORDER BY name"
        return "SELECT name as table_name FROM sys.tables ORDER BY name"
    
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """SQL Server: 从sys.columns获取表信息"""
        schema_clause = f"AND s.name = '{schema}'" if schema else ""
        return f"""
            SELECT 
                c.name as column_name,
                t.name as data_type,
                CASE WHEN c.is_nullable = 1 THEN 'YES' ELSE 'NO' END as is_nullable,
                ISNULL(dc.definition, '') as column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN 'PRI' ELSE '' END as column_key,
                ISNULL(ep.value, '') as column_comment
            FROM sys.columns c
            INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
            INNER JOIN sys.tables tb ON c.object_id = tb.object_id
            INNER JOIN sys.schemas s ON tb.schema_id = s.schema_id
            LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
            LEFT JOIN sys.extended_properties ep ON ep.major_id = c.object_id 
                AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
            LEFT JOIN (
                SELECT ku.table_name, ku.column_name
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                WHERE ku.table_name = '{table_name}'
            ) pk ON c.name = pk.column_name
            WHERE tb.name = '{table_name}' {schema_clause}
            ORDER BY c.column_id
        """


class OracleAdapter(SQLDialectAdapter):
    """Oracle方言适配器"""
    
    def escape_identifier(self, identifier: str) -> str:
        """Oracle使用双引号转义标识符（区分大小写）"""
        if not identifier:
            return identifier
        if identifier.startswith('"') and identifier.endswith('"'):
            return identifier
        return f'"{identifier.upper()}"'
    
    def build_limit_clause(self, limit: Optional[int] = None, offset: Optional[int] = None) -> str:
        """Oracle 12c+: FETCH FIRST n ROWS ONLY OFFSET m ROWS"""
        if limit is None:
            return ""
        if offset is None or offset == 0:
            return f"FETCH FIRST {limit} ROWS ONLY"
        return f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
    
    def get_table_names_query(self, schema: Optional[str] = None) -> str:
        """Oracle: 从user_tables或all_tables获取表列表"""
        if schema:
            schema_escaped = schema.replace("'", "''")  # 防止SQL注入
            return f"SELECT table_name FROM all_tables WHERE owner = UPPER('{schema_escaped}') ORDER BY table_name"
        return "SELECT table_name FROM user_tables ORDER BY table_name"
    
    def get_table_info_query(self, table_name: str, schema: Optional[str] = None) -> str:
        """Oracle: 从user_tab_columns或all_tab_columns获取表信息"""
        schema_clause = f"AND owner = UPPER('{schema}')" if schema else ""
        return f"""
            SELECT 
                column_name,
                data_type,
                nullable as is_nullable,
                data_default as column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN 'PRI' ELSE '' END as column_key,
                '' as column_comment
            FROM all_tab_columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM all_cons_columns ku
                JOIN all_constraints cu ON ku.constraint_name = cu.constraint_name
                WHERE cu.constraint_type = 'P' 
                AND ku.table_name = UPPER('{table_name}')
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = UPPER('{table_name}') {schema_clause}
            ORDER BY c.column_id
        """


class SQLDialectFactory:
    """SQL方言适配器工厂"""
    
    _adapters = {
        "mysql": MySQLAdapter(),
        "postgresql": PostgreSQLAdapter(),
        "sqlite": SQLiteAdapter(),
        "sqlserver": SQLServerAdapter(),
        "oracle": OracleAdapter(),
    }
    
    @classmethod
    def get_adapter(cls, db_type: str) -> SQLDialectAdapter:
        """
        获取指定数据库类型的SQL方言适配器
        
        Args:
            db_type: 数据库类型
            
        Returns:
            SQL方言适配器实例
        """
        db_type = db_type.lower() if db_type else "mysql"
        adapter = cls._adapters.get(db_type)
        if not adapter:
            logger.warning(f"未找到数据库类型 {db_type} 的适配器，使用MySQL适配器")
            return cls._adapters["mysql"]
        return adapter
    
    @classmethod
    def register_adapter(cls, db_type: str, adapter: SQLDialectAdapter):
        """
        注册自定义适配器
        
        Args:
            db_type: 数据库类型
            adapter: 适配器实例
        """
        cls._adapters[db_type.lower()] = adapter

