"""
SQLite数据库探查适配器
提供SQLite特定的探查SQL查询
"""
from typing import Optional, Dict, Any
from loguru import logger


class SQLiteAdapter:
    """SQLite数据库探查适配器"""
    
    @staticmethod
    def get_database_capacity_query(database_name: str) -> str:
        """
        获取库容量画像SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            
        Returns:
            SQL查询语句
        """
        return """
            SELECT 
                'main' AS database_name,
                ROUND(SUM(pgsize) / 1024.0 / 1024.0, 2) AS total_mb,
                COUNT(*) AS table_cnt
            FROM dbstat
        """
    
    @staticmethod
    def get_object_count_queries(database_name: str) -> Dict[str, str]:
        """
        获取对象数量查询SQL字典
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            
        Returns:
            包含各种对象数量查询的字典
        """
        return {
            "tables": "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            "views": "SELECT COUNT(*) FROM sqlite_master WHERE type='view'",
            "triggers": "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'",
        }
    
    @staticmethod
    def get_top_n_tables_query(database_name: str, n: int = 10) -> str:
        """
        获取TOP N大表SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            n: 返回前N个表
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                name AS table_name,
                ROUND((SELECT pgsize FROM dbstat WHERE name = t.name) / 1024.0 / 1024.0, 2) AS size_mb
            FROM sqlite_master t
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY (SELECT pgsize FROM dbstat WHERE name = t.name) DESC
            LIMIT {n}
        """
    
    @staticmethod
    def get_table_info_query(database_name: str, table_name: str) -> str:
        """
        获取表信息SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                name AS table_name,
                (SELECT COUNT(*) FROM {table_name}) AS row_count,
                ROUND((SELECT pgsize FROM dbstat WHERE name = '{table_name}') / 1024.0 / 1024.0, 2) AS size_mb
            FROM sqlite_master
            WHERE type='table' AND name = '{table_name}'
        """
    
    @staticmethod
    def get_table_columns_query(database_name: str, table_name: str) -> str:
        """
        获取表字段信息SQL（使用PRAGMA）
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            
        Returns:
            SQL查询语句（返回PRAGMA table_info的结果）
        """
        # SQLite使用PRAGMA，需要在代码中特殊处理
        return f"PRAGMA table_info({table_name})"
    
    @staticmethod
    def get_primary_key_query(database_name: str, table_name: str) -> str:
        """
        获取主键信息SQL（使用PRAGMA）
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            
        Returns:
            SQL查询语句（返回PRAGMA table_info的结果，pk=1的字段）
        """
        # SQLite使用PRAGMA，需要在代码中特殊处理
        return f"PRAGMA table_info({table_name})"
    
    @staticmethod
    def get_indexes_query(database_name: str, table_name: str) -> str:
        """
        获取索引信息SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                name AS index_name,
                sql AS index_definition
            FROM sqlite_master
            WHERE type='index' AND tbl_name = '{table_name}'
        """
    
    @staticmethod
    def get_foreign_keys_query(database_name: str, table_name: str) -> str:
        """
        获取外键信息SQL（使用PRAGMA）
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            
        Returns:
            SQL查询语句（返回PRAGMA foreign_key_list的结果）
        """
        # SQLite使用PRAGMA，需要在代码中特殊处理
        return f"PRAGMA foreign_key_list({table_name})"
    
    @staticmethod
    def get_column_statistics_query(database_name: str, table_name: str, column_name: str) -> str:
        """
        获取字段统计信息SQL（基础探查）
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            column_name: 字段名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                COUNT(*) AS total_cnt,
                COUNT([{column_name}]) AS non_null_cnt,
                COUNT(DISTINCT [{column_name}]) AS distinct_cnt
            FROM [{table_name}]
        """
    
    @staticmethod
    def get_column_value_range_query(database_name: str, table_name: str, column_name: str, data_type: str) -> str:
        """
        获取字段值域查询SQL（高级探查）
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            column_name: 字段名
            data_type: 数据类型
            
        Returns:
            SQL查询语句
        """
        if 'INT' in data_type.upper() or 'REAL' in data_type.upper() or 'NUMERIC' in data_type.upper():
            return f"""
                SELECT 
                    MAX([{column_name}]) AS max_value,
                    MIN([{column_name}]) AS min_value,
                    AVG([{column_name}]) AS avg_value,
                    SUM(CASE WHEN [{column_name}] = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN [{column_name}] < 0 THEN 1 ELSE 0 END) AS negative_count
                FROM [{table_name}]
            """
        elif 'TEXT' in data_type.upper() or 'VARCHAR' in data_type.upper() or 'CHAR' in data_type.upper():
            return f"""
                SELECT 
                    MAX(LENGTH([{column_name}])) AS max_length,
                    MIN(LENGTH([{column_name}])) AS min_length,
                    AVG(LENGTH([{column_name}])) AS avg_length
                FROM [{table_name}]
                WHERE [{column_name}] IS NOT NULL
            """
        elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
            return f"""
                SELECT 
                    MAX([{column_name}]) AS max_value,
                    MIN([{column_name}]) AS min_value
                FROM [{table_name}]
            """
        else:
            return f"""
                SELECT 
                    COUNT(*) AS total_cnt
                FROM [{table_name}]
            """
    
    @staticmethod
    def get_top_values_query(database_name: str, table_name: str, column_name: str, limit: int = 20) -> str:
        """
        获取Top N高频值SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            column_name: 字段名
            limit: 返回前N个值
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                [{column_name}] AS value,
                COUNT(*) AS count
            FROM [{table_name}]
            WHERE [{column_name}] IS NOT NULL
            GROUP BY [{column_name}]
            ORDER BY count DESC
            LIMIT {limit}
        """
    
    @staticmethod
    def get_sample_data_query(database_name: str, table_name: str, limit: int = 10) -> str:
        """
        获取示例数据SQL
        
        Args:
            database_name: 数据库名（SQLite中通常不使用）
            table_name: 表名
            limit: 返回行数
            
        Returns:
            SQL查询语句
        """
        return f"SELECT * FROM [{table_name}] LIMIT {limit}"

