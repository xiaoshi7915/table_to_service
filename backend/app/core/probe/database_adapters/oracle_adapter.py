"""
Oracle数据库探查适配器
提供Oracle特定的探查SQL查询
"""
from typing import Optional, Dict, Any
from loguru import logger


class OracleAdapter:
    """Oracle数据库探查适配器"""
    
    @staticmethod
    def get_database_capacity_query(database_name: str) -> str:
        """
        获取库容量画像SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                owner,
                ROUND(SUM(bytes) / 1024 / 1024, 2) AS total_mb,
                COUNT(*) AS table_cnt
            FROM dba_segments
            WHERE owner = UPPER('{database_name}')
                AND segment_type = 'TABLE'
            GROUP BY owner
            ORDER BY total_mb DESC
        """
    
    @staticmethod
    def get_object_count_queries(database_name: str) -> Dict[str, str]:
        """
        获取对象数量查询SQL字典
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            
        Returns:
            包含各种对象数量查询的字典
        """
        return {
            "tables": f"SELECT COUNT(*) FROM all_tables WHERE owner = UPPER('{database_name}')",
            "views": f"SELECT COUNT(*) FROM all_views WHERE owner = UPPER('{database_name}')",
            "functions": f"SELECT COUNT(*) FROM all_procedures WHERE owner = UPPER('{database_name}') AND object_type = 'FUNCTION'",
            "procedures": f"SELECT COUNT(*) FROM all_procedures WHERE owner = UPPER('{database_name}') AND object_type = 'PROCEDURE'",
            "triggers": f"SELECT COUNT(*) FROM all_triggers WHERE owner = UPPER('{database_name}')",
            "sequences": f"SELECT COUNT(*) FROM all_sequences WHERE sequence_owner = UPPER('{database_name}')",
        }
    
    @staticmethod
    def get_top_n_tables_query(database_name: str, n: int = 10) -> str:
        """
        获取TOP N大表SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            n: 返回前N个表
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT * FROM (
                SELECT 
                    table_name,
                    ROUND(bytes / 1024 / 1024, 2) AS size_mb,
                    num_rows
                FROM all_tables
                WHERE owner = UPPER('{database_name}')
                ORDER BY bytes DESC
            ) WHERE ROWNUM <= {n}
        """
    
    @staticmethod
    def get_table_info_query(database_name: str, table_name: str) -> str:
        """
        获取表信息SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                table_name,
                num_rows AS row_count,
                ROUND(blocks * 8 / 1024, 2) AS size_mb,
                avg_row_len AS avg_row_length
            FROM all_tables
            WHERE owner = UPPER('{database_name}') AND table_name = UPPER('{table_name}')
        """
    
    @staticmethod
    def get_table_columns_query(database_name: str, table_name: str) -> str:
        """
        获取表字段信息SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                column_name,
                data_type,
                data_length,
                nullable,
                data_default,
                (SELECT comments FROM all_col_comments 
                 WHERE owner = UPPER('{database_name}') 
                 AND table_name = UPPER('{table_name}') 
                 AND column_name = ac.column_name) AS column_comment
            FROM all_tab_columns ac
            WHERE owner = UPPER('{database_name}') AND table_name = UPPER('{table_name}')
            ORDER BY column_id
        """
    
    @staticmethod
    def get_primary_key_query(database_name: str, table_name: str) -> str:
        """
        获取主键信息SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                column_name
            FROM all_cons_columns
            WHERE owner = UPPER('{database_name}')
                AND table_name = UPPER('{table_name}')
                AND constraint_name = (
                    SELECT constraint_name 
                    FROM all_constraints 
                    WHERE owner = UPPER('{database_name}')
                        AND table_name = UPPER('{table_name}')
                        AND constraint_type = 'P'
                )
            ORDER BY position
        """
    
    @staticmethod
    def get_indexes_query(database_name: str, table_name: str) -> str:
        """
        获取索引信息SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                index_name,
                column_name,
                column_position,
                uniqueness
            FROM all_ind_columns
            WHERE table_owner = UPPER('{database_name}') AND table_name = UPPER('{table_name}')
            ORDER BY index_name, column_position
        """
    
    @staticmethod
    def get_foreign_keys_query(database_name: str, table_name: str) -> str:
        """
        获取外键信息SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                constraint_name,
                column_name,
                r_owner AS referenced_owner,
                r_table_name AS referenced_table_name,
                r_column_name AS referenced_column_name
            FROM all_cons_columns acc
            JOIN all_constraints ac ON acc.constraint_name = ac.constraint_name
            WHERE acc.owner = UPPER('{database_name}')
                AND acc.table_name = UPPER('{table_name}')
                AND ac.constraint_type = 'R'
            ORDER BY acc.position
        """
    
    @staticmethod
    def get_column_statistics_query(database_name: str, table_name: str, column_name: str) -> str:
        """
        获取字段统计信息SQL（基础探查）
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            column_name: 字段名
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT 
                COUNT(*) AS total_cnt,
                COUNT({column_name}) AS non_null_cnt,
                COUNT(DISTINCT {column_name}) AS distinct_cnt
            FROM {database_name}.{table_name}
        """
    
    @staticmethod
    def get_column_value_range_query(database_name: str, table_name: str, column_name: str, data_type: str) -> str:
        """
        获取字段值域查询SQL（高级探查）
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            column_name: 字段名
            data_type: 数据类型
            
        Returns:
            SQL查询语句
        """
        if 'NUMBER' in data_type.upper() or 'INT' in data_type.upper() or 'FLOAT' in data_type.upper():
            return f"""
                SELECT 
                    MAX({column_name}) AS max_value,
                    MIN({column_name}) AS min_value,
                    AVG({column_name}) AS avg_value,
                    SUM(CASE WHEN {column_name} = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN {column_name} < 0 THEN 1 ELSE 0 END) AS negative_count
                FROM {database_name}.{table_name}
            """
        elif 'VARCHAR' in data_type.upper() or 'CHAR' in data_type.upper() or 'CLOB' in data_type.upper():
            return f"""
                SELECT 
                    MAX(LENGTH({column_name})) AS max_length,
                    MIN(LENGTH({column_name})) AS min_length,
                    AVG(LENGTH({column_name})) AS avg_length
                FROM {database_name}.{table_name}
                WHERE {column_name} IS NOT NULL
            """
        elif 'DATE' in data_type.upper() or 'TIMESTAMP' in data_type.upper():
            return f"""
                SELECT 
                    MAX({column_name}) AS max_value,
                    MIN({column_name}) AS min_value
                FROM {database_name}.{table_name}
            """
        else:
            return f"""
                SELECT 
                    COUNT(*) AS total_cnt
                FROM {database_name}.{table_name}
            """
    
    @staticmethod
    def get_top_values_query(database_name: str, table_name: str, column_name: str, limit: int = 20) -> str:
        """
        获取Top N高频值SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            column_name: 字段名
            limit: 返回前N个值
            
        Returns:
            SQL查询语句
        """
        return f"""
            SELECT * FROM (
                SELECT 
                    {column_name} AS value,
                    COUNT(*) AS count
                FROM {database_name}.{table_name}
                WHERE {column_name} IS NOT NULL
                GROUP BY {column_name}
                ORDER BY count DESC
            ) WHERE ROWNUM <= {limit}
        """
    
    @staticmethod
    def get_sample_data_query(database_name: str, table_name: str, limit: int = 10) -> str:
        """
        获取示例数据SQL
        
        Args:
            database_name: 数据库名（Oracle中使用用户名）
            table_name: 表名
            limit: 返回行数
            
        Returns:
            SQL查询语句
        """
        return f"SELECT * FROM {database_name}.{table_name} WHERE ROWNUM <= {limit}"

