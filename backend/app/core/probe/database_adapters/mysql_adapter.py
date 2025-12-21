"""
MySQL数据库探查适配器
提供MySQL特定的探查SQL查询
"""
from typing import Optional, Dict, Any
from loguru import logger


class MySQLAdapter:
    """MySQL数据库探查适配器"""
    
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
                table_schema,
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_MB,
                COUNT(*) AS table_cnt
            FROM information_schema.tables
            WHERE table_schema = '{database_name}'
            GROUP BY table_schema
            ORDER BY total_MB DESC
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
            "tables": f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{database_name}'",
            "views": f"SELECT COUNT(*) FROM information_schema.views WHERE table_schema = '{database_name}'",
            "functions": f"SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = '{database_name}' AND routine_type = 'FUNCTION'",
            "procedures": f"SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = '{database_name}' AND routine_type = 'PROCEDURE'",
            "triggers": f"SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = '{database_name}'",
            "events": f"SELECT COUNT(*) FROM information_schema.events WHERE event_schema = '{database_name}'",
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
            SELECT 
                table_name,
                ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_MB,
                table_rows
            FROM information_schema.tables
            WHERE table_schema = '{database_name}'
            ORDER BY (data_length + index_length) DESC
            LIMIT {n}
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
                table_name,
                table_rows,
                ROUND(data_length / 1024 / 1024, 2) AS data_MB,
                ROUND(index_length / 1024 / 1024, 2) AS idx_MB,
                ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_MB,
                ROUND(data_length / table_rows, 2) AS avg_row_length
            FROM information_schema.tables
            WHERE table_schema = '{database_name}' AND table_name = '{table_name}'
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
                column_name,
                data_type,
                column_type,
                is_nullable,
                column_default,
                column_comment,
                extra
            FROM information_schema.columns
            WHERE table_schema = '{database_name}' AND table_name = '{table_name}'
            ORDER BY ordinal_position
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
                column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = '{database_name}' 
                AND table_name = '{table_name}'
                AND constraint_name = 'PRIMARY'
            ORDER BY ordinal_position
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
                index_name,
                column_name,
                seq_in_index,
                non_unique,
                index_type
            FROM information_schema.statistics
            WHERE table_schema = '{database_name}' AND table_name = '{table_name}'
            ORDER BY index_name, seq_in_index
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
                constraint_name,
                column_name,
                referenced_table_schema,
                referenced_table_name,
                referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = '{database_name}' 
                AND table_name = '{table_name}'
                AND referenced_table_name IS NOT NULL
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
                COUNT(`{column_name}`) AS non_null_cnt,
                COUNT(DISTINCT `{column_name}`) AS distinct_cnt
            FROM `{database_name}`.`{table_name}`
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
        # 根据数据类型选择不同的查询
        if 'int' in data_type.lower() or 'decimal' in data_type.lower() or 'float' in data_type.lower() or 'double' in data_type.lower():
            return f"""
                SELECT 
                    MAX(`{column_name}`) AS max_value,
                    MIN(`{column_name}`) AS min_value,
                    AVG(`{column_name}`) AS avg_value,
                    SUM(CASE WHEN `{column_name}` = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN `{column_name}` < 0 THEN 1 ELSE 0 END) AS negative_count
                FROM `{database_name}`.`{table_name}`
            """
        elif 'varchar' in data_type.lower() or 'char' in data_type.lower() or 'text' in data_type.lower():
            return f"""
                SELECT 
                    MAX(LENGTH(`{column_name}`)) AS max_length,
                    MIN(LENGTH(`{column_name}`)) AS min_length,
                    AVG(LENGTH(`{column_name}`)) AS avg_length
                FROM `{database_name}`.`{table_name}`
                WHERE `{column_name}` IS NOT NULL
            """
        elif 'date' in data_type.lower() or 'time' in data_type.lower():
            return f"""
                SELECT 
                    MAX(`{column_name}`) AS max_value,
                    MIN(`{column_name}`) AS min_value
                FROM `{database_name}`.`{table_name}`
            """
        else:
            return f"""
                SELECT 
                    COUNT(*) AS total_cnt
                FROM `{database_name}`.`{table_name}`
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
            SELECT 
                `{column_name}` AS value,
                COUNT(*) AS count
            FROM `{database_name}`.`{table_name}`
            WHERE `{column_name}` IS NOT NULL
            GROUP BY `{column_name}`
            ORDER BY count DESC
            LIMIT {limit}
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
        return f"SELECT * FROM `{database_name}`.`{table_name}` LIMIT {limit}"

