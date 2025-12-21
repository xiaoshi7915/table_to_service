"""
PostgreSQL数据库探查适配器
提供PostgreSQL特定的探查SQL查询
"""
from typing import Optional, Dict, Any
from loguru import logger


class PostgreSQLAdapter:
    """PostgreSQL数据库探查适配器"""
    
    @staticmethod
    def get_database_capacity_query(database_name: str, schema_name: str = "public") -> str:
        """
        获取库容量画像SQL
        
        Args:
            database_name: 数据库名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                schemaname,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                COUNT(*) AS table_cnt
            FROM pg_tables
            WHERE schemaname = '{schema_name}'
            GROUP BY schemaname
            ORDER BY size_bytes DESC
        """
    
    @staticmethod
    def get_object_count_queries(database_name: str, schema_name: str = "public") -> Dict[str, str]:
        """
        获取对象数量查询SQL字典
        
        Args:
            database_name: 数据库名
            schema_name: Schema名
            
        Returns:
            包含各种对象数量查询的字典
        """
        return {
            "tables": f"SELECT COUNT(*) FROM pg_tables WHERE schemaname = '{schema_name}'",
            "views": f"SELECT COUNT(*) FROM pg_views WHERE schemaname = '{schema_name}'",
            "functions": f"SELECT COUNT(*) FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_name}')",
            "procedures": f"SELECT COUNT(*) FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_name}') AND prokind = 'p'",
            "triggers": f"SELECT COUNT(*) FROM pg_trigger WHERE tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_name}'))",
            "sequences": f"SELECT COUNT(*) FROM pg_sequence WHERE schemaname = '{schema_name}'",
        }
    
    @staticmethod
    def get_top_n_tables_query(database_name: str, schema_name: str = "public", n: int = 10) -> str:
        """
        获取TOP N大表SQL
        
        Args:
            database_name: 数据库名
            schema_name: Schema名
            n: 返回前N个表
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                tablename AS table_name,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = '{schema_name}'
            ORDER BY size_bytes DESC
            LIMIT {n}
        """
    
    @staticmethod
    def get_table_info_query(database_name: str, table_name: str, schema_name: str = "public") -> str:
        """
        获取表信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                schemaname,
                tablename AS table_name,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                pg_total_relation_size(schemaname||'.'||tablename) AS total_size_bytes,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS data_size,
                pg_relation_size(schemaname||'.'||tablename) AS data_size_bytes,
                (SELECT reltuples::bigint FROM pg_class WHERE relname = tablename) AS row_count
            FROM pg_tables
            WHERE schemaname = '{schema_name}' AND tablename = '{table_name}'
        """
    
    @staticmethod
    def get_table_columns_query(database_name: str, table_name: str, schema_name: str = "public") -> str:
        """
        获取表字段信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                column_name,
                data_type,
                udt_name,
                is_nullable,
                column_default,
                (SELECT description FROM pg_description 
                 WHERE objoid = (SELECT oid FROM pg_class WHERE relname = '{table_name}') 
                 AND objsubid = ordinal_position) AS column_comment
            FROM information_schema.columns
            WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """
    
    @staticmethod
    def get_primary_key_query(database_name: str, table_name: str, schema_name: str = "public") -> str:
        """
        获取主键信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                a.attname AS column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = '{schema_name}.{table_name}'::regclass
                AND i.indisprimary
            ORDER BY a.attnum
        """
    
    @staticmethod
    def get_indexes_query(database_name: str, table_name: str, schema_name: str = "public") -> str:
        """
        获取索引信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                indexname AS index_name,
                indexdef AS index_definition
            FROM pg_indexes
            WHERE schemaname = '{schema_name}' AND tablename = '{table_name}'
        """
    
    @staticmethod
    def get_foreign_keys_query(database_name: str, table_name: str, schema_name: str = "public") -> str:
        """
        获取外键信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_schema AS referenced_table_schema,
                ccu.table_name AS referenced_table_name,
                ccu.column_name AS referenced_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = '{schema_name}'
                AND tc.table_name = '{table_name}'
        """
    
    @staticmethod
    def get_column_statistics_query(database_name: str, table_name: str, column_name: str, schema_name: str = "public") -> str:
        """
        获取字段统计信息SQL（基础探查）
        
        Args:
            database_name: 数据库名
            table_name: 表名
            column_name: 字段名
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                COUNT(*) AS total_cnt,
                COUNT({column_name}) AS non_null_cnt,
                COUNT(DISTINCT {column_name}) AS distinct_cnt
            FROM {schema_name}.{table_name}
        """
    
    @staticmethod
    def get_column_value_range_query(database_name: str, table_name: str, column_name: str, data_type: str, schema_name: str = "public") -> str:
        """
        获取字段值域查询SQL（高级探查）
        
        Args:
            database_name: 数据库名
            table_name: 表名
            column_name: 字段名
            data_type: 数据类型
            schema_name: Schema名
            
        Returns:
            SQL查询语句
        """
        if 'int' in data_type.lower() or 'numeric' in data_type.lower() or 'decimal' in data_type.lower() or 'real' in data_type.lower() or 'double' in data_type.lower():
            return f"""
                SELECT 
                    MAX({column_name}) AS max_value,
                    MIN({column_name}) AS min_value,
                    AVG({column_name}) AS avg_value,
                    SUM(CASE WHEN {column_name} = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN {column_name} < 0 THEN 1 ELSE 0 END) AS negative_count
                FROM {schema_name}.{table_name}
            """
        elif 'varchar' in data_type.lower() or 'char' in data_type.lower() or 'text' in data_type.lower():
            return f"""
                SELECT 
                    MAX(LENGTH({column_name})) AS max_length,
                    MIN(LENGTH({column_name})) AS min_length,
                    AVG(LENGTH({column_name})) AS avg_length
                FROM {schema_name}.{table_name}
                WHERE {column_name} IS NOT NULL
            """
        elif 'date' in data_type.lower() or 'time' in data_type.lower() or 'timestamp' in data_type.lower():
            return f"""
                SELECT 
                    MAX({column_name}) AS max_value,
                    MIN({column_name}) AS min_value
                FROM {schema_name}.{table_name}
            """
        else:
            return f"""
                SELECT 
                    COUNT(*) AS total_cnt
                FROM {schema_name}.{table_name}
            """
    
    @staticmethod
    def get_top_values_query(database_name: str, table_name: str, column_name: str, schema_name: str = "public", limit: int = 20) -> str:
        """
        获取Top N高频值SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            column_name: 字段名
            schema_name: Schema名
            limit: 返回前N个值
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                {column_name} AS value,
                COUNT(*) AS count
            FROM {schema_name}.{table_name}
            WHERE {column_name} IS NOT NULL
            GROUP BY {column_name}
            ORDER BY count DESC
            LIMIT {limit}
        """
    
    @staticmethod
    def get_sample_data_query(database_name: str, table_name: str, schema_name: str = "public", limit: int = 10) -> str:
        """
        获取示例数据SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            schema_name: Schema名
            limit: 返回行数
            
        Returns:
            SQL查询语句
        """
        return f"SELECT * FROM {schema_name}.{table_name} LIMIT {limit}"

