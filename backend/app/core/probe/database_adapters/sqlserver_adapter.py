"""
SQL Server数据库探查适配器
提供SQL Server特定的探查SQL查询
"""
from typing import Optional, Dict, Any
from loguru import logger


class SQLServerAdapter:
    """SQL Server数据库探查适配器"""
    
    @staticmethod
    def get_database_capacity_query(database_name: str) -> str:
        """
        获取库容量画像SQL
        
        Args:
            database_name: 数据库名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                DB_NAME() AS database_name,
                SUM(size * 8 / 1024.0) AS total_size_mb,
                COUNT(*) AS table_cnt
            FROM sys.master_files
            WHERE database_id = DB_ID('{database_name}')
        """
    
    @staticmethod
    def get_object_count_queries(database_name: str) -> Dict[str, str]:
        """
        获取对象数量查询SQL字典
        
        Args:
            database_name: 数据库名
            
        Returns:
            包含各种对象数量查询的字典
        """
        return {
            "tables": f"SELECT COUNT(*) FROM {database_name}.sys.tables",
            "views": f"SELECT COUNT(*) FROM {database_name}.sys.views",
            "functions": f"SELECT COUNT(*) FROM {database_name}.sys.objects WHERE type = 'FN' OR type = 'IF'",
            "procedures": f"SELECT COUNT(*) FROM {database_name}.sys.objects WHERE type = 'P'",
            "triggers": f"SELECT COUNT(*) FROM {database_name}.sys.triggers",
        }
    
    @staticmethod
    def get_top_n_tables_query(database_name: str, n: int = 10) -> str:
        """
        获取TOP N大表SQL
        
        Args:
            database_name: 数据库名
            n: 返回前N个表
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT TOP {n}
                t.name AS table_name,
                p.rows AS row_count,
                SUM(a.total_pages) * 8 / 1024.0 AS size_mb
            FROM {database_name}.sys.tables t
            INNER JOIN {database_name}.sys.indexes i ON t.object_id = i.object_id
            INNER JOIN {database_name}.sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
            INNER JOIN {database_name}.sys.allocation_units a ON p.partition_id = a.container_id
            GROUP BY t.name, p.rows
            ORDER BY size_mb DESC
        """
    
    @staticmethod
    def get_table_info_query(database_name: str, table_name: str) -> str:
        """
        获取表信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                t.name AS table_name,
                p.rows AS row_count,
                SUM(a.total_pages) * 8 / 1024.0 AS total_size_mb,
                SUM(a.used_pages) * 8 / 1024.0 AS used_size_mb
            FROM {database_name}.sys.tables t
            INNER JOIN {database_name}.sys.indexes i ON t.object_id = i.object_id
            INNER JOIN {database_name}.sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
            INNER JOIN {database_name}.sys.allocation_units a ON p.partition_id = a.container_id
            WHERE t.name = '{table_name}'
            GROUP BY t.name, p.rows
        """
    
    @staticmethod
    def get_table_columns_query(database_name: str, table_name: str) -> str:
        """
        获取表字段信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                c.name AS column_name,
                t.name AS data_type,
                c.max_length,
                c.is_nullable,
                c.default_object_id,
                ep.value AS column_comment
            FROM {database_name}.sys.columns c
            INNER JOIN {database_name}.sys.types t ON c.user_type_id = t.user_type_id
            LEFT JOIN {database_name}.sys.extended_properties ep ON ep.major_id = c.object_id AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
            WHERE c.object_id = OBJECT_ID('{database_name}.dbo.{table_name}')
            ORDER BY c.column_id
        """
    
    @staticmethod
    def get_primary_key_query(database_name: str, table_name: str) -> str:
        """
        获取主键信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                c.name AS column_name
            FROM {database_name}.sys.indexes i
            INNER JOIN {database_name}.sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN {database_name}.sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.is_primary_key = 1
                AND i.object_id = OBJECT_ID('{database_name}.dbo.{table_name}')
            ORDER BY ic.key_ordinal
        """
    
    @staticmethod
    def get_indexes_query(database_name: str, table_name: str) -> str:
        """
        获取索引信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                i.name AS index_name,
                c.name AS column_name,
                i.is_unique,
                i.type_desc
            FROM {database_name}.sys.indexes i
            INNER JOIN {database_name}.sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN {database_name}.sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.object_id = OBJECT_ID('{database_name}.dbo.{table_name}')
            ORDER BY i.name, ic.key_ordinal
        """
    
    @staticmethod
    def get_foreign_keys_query(database_name: str, table_name: str) -> str:
        """
        获取外键信息SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                fk.name AS constraint_name,
                c.name AS column_name,
                OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_table_schema,
                OBJECT_NAME(fk.referenced_object_id) AS referenced_table_name,
                rc.name AS referenced_column_name
            FROM {database_name}.sys.foreign_keys fk
            INNER JOIN {database_name}.sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN {database_name}.sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
            INNER JOIN {database_name}.sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id
            WHERE fk.parent_object_id = OBJECT_ID('{database_name}.dbo.{table_name}')
        """
    
    @staticmethod
    def get_column_statistics_query(database_name: str, table_name: str, column_name: str) -> str:
        """
        获取字段统计信息SQL（基础探查）
        
        Args:
            database_name: 数据库名
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
            FROM [{database_name}].[dbo].[{table_name}]
        """
    
    @staticmethod
    def get_column_value_range_query(database_name: str, table_name: str, column_name: str, data_type: str) -> str:
        """
        获取字段值域查询SQL（高级探查）
        
        Args:
            database_name: 数据库名
            table_name: 表名
            column_name: 字段名
            data_type: 数据类型
            
        Returns:
            SQL查询语句
        """
        if 'int' in data_type.lower() or 'decimal' in data_type.lower() or 'float' in data_type.lower() or 'money' in data_type.lower():
            return f"""
                SELECT 
                    MAX([{column_name}]) AS max_value,
                    MIN([{column_name}]) AS min_value,
                    AVG(CAST([{column_name}] AS FLOAT)) AS avg_value,
                    SUM(CASE WHEN [{column_name}] = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN [{column_name}] < 0 THEN 1 ELSE 0 END) AS negative_count
                FROM [{database_name}].[dbo].[{table_name}]
            """
        elif 'varchar' in data_type.lower() or 'char' in data_type.lower() or 'text' in data_type.lower() or 'nvarchar' in data_type.lower():
            return f"""
                SELECT 
                    MAX(LEN([{column_name}])) AS max_length,
                    MIN(LEN([{column_name}])) AS min_length,
                    AVG(CAST(LEN([{column_name}]) AS FLOAT)) AS avg_length
                FROM [{database_name}].[dbo].[{table_name}]
                WHERE [{column_name}] IS NOT NULL
            """
        elif 'date' in data_type.lower() or 'time' in data_type.lower():
            return f"""
                SELECT 
                    MAX([{column_name}]) AS max_value,
                    MIN([{column_name}]) AS min_value
                FROM [{database_name}].[dbo].[{table_name}]
            """
        else:
            return f"""
                SELECT 
                    COUNT(*) AS total_cnt
                FROM [{database_name}].[dbo].[{table_name}]
            """
    
    @staticmethod
    def get_top_values_query(database_name: str, table_name: str, column_name: str, limit: int = 20) -> str:
        """
        获取Top N高频值SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            column_name: 字段名
            limit: 返回前N个值
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT TOP {limit}
                [{column_name}] AS value,
                COUNT(*) AS count
            FROM [{database_name}].[dbo].[{table_name}]
            WHERE [{column_name}] IS NOT NULL
            GROUP BY [{column_name}]
            ORDER BY count DESC
        """
    
    @staticmethod
    def get_sample_data_query(database_name: str, table_name: str, limit: int = 10) -> str:
        """
        获取示例数据SQL
        
        Args:
            database_name: 数据库名
            table_name: 表名
            limit: 返回行数
            
        Returns:
            SQL查询语句
        """
        return f"SELECT TOP {limit} * FROM [{database_name}].[dbo].[{table_name}]"

