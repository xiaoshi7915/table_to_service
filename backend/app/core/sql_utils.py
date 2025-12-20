"""
SQL执行公共工具函数
提取interface_executor和sql_executor中的公共逻辑
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from loguru import logger

from app.core.sql_dialect import SQLDialectFactory
from app.core.log_sanitizer import safe_log_sql, safe_log_params


def process_sql_params(
    sql: str,
    params: Dict[str, Any],
    entry_mode: str = "expert"
) -> Tuple[str, Dict[str, Any]]:
    """
    处理SQL参数（移除缺失参数，构建参数字典）
    
    Args:
        sql: SQL语句
        params: 参数字典
        entry_mode: 入口模式（expert/query/graphical）
        
    Returns:
        (处理后的SQL, 参数字典) 元组
    """
    query_params = {}
    
    if entry_mode in ["expert", "query"]:
        # 检查SQL中是否有未替换的占位符
        placeholder_pattern = r':(\w+)'
        placeholders_in_sql = re.findall(placeholder_pattern, sql)

        # 宽松模式：如果参数缺失，将对应的WHERE条件移除
        missing_params = [p for p in placeholders_in_sql if p not in params]
        if missing_params:
            # 移除缺失参数对应的WHERE条件
            for missing_param in missing_params:
                # 使用更精确的正则表达式，确保精确匹配参数名
                placeholder_pattern = rf'(?:\s+WHERE\s+|\s+(?:AND|OR)\s+)\b{re.escape(missing_param)}\b\s*=\s*:{re.escape(missing_param)}\b'
                sql = re.sub(placeholder_pattern, '', sql, flags=re.IGNORECASE)
            
            # 清理可能出现的多余空格和AND/OR（多次清理确保干净）
            for _ in range(3):
                sql_before = sql
                sql = re.sub(r'\s+AND\s+AND', ' AND', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\s+OR\s+OR', ' OR', sql, flags=re.IGNORECASE)
                sql = re.sub(r'WHERE\s+AND\s+', 'WHERE ', sql, flags=re.IGNORECASE)
                sql = re.sub(r'WHERE\s+OR\s+', 'WHERE ', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\s+WHERE\s+WHERE', ' WHERE', sql, flags=re.IGNORECASE)
                if sql == sql_before:
                    break
            
            # 如果WHERE子句为空，移除整个WHERE关键字
            sql = re.sub(r'\s+WHERE\s*$', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\s+WHERE\s*;', ';', sql, flags=re.IGNORECASE)
        
        # 构建参数化查询的参数字典（只包含SQL中实际存在的占位符）
        for key, value in params.items():
            placeholder = f":{key}"
            if placeholder in sql:
                query_params[key] = value
    
    return sql, query_params


def execute_sql_query(
    db: Session,
    sql: str,
    query_params: Optional[Dict[str, Any]] = None
) -> Tuple[Any, List[str]]:
    """
    执行SQL查询（公共函数）
    
    Args:
        db: 数据库会话
        sql: SQL语句
        query_params: 参数字典（可选）
        
    Returns:
        (查询结果, 列名列表) 元组
    """
    if query_params:
        result = db.execute(text(sql), query_params)
    else:
        result = db.execute(text(sql))
    
    rows = result.fetchall()
    columns = list(result.keys())
    
    return rows, columns


def convert_rows_to_dicts(
    rows: List[Any],
    columns: List[str]
) -> List[Dict[str, Any]]:
    """
    将查询结果行转换为字典列表（公共函数）
    
    Args:
        rows: 查询结果行
        columns: 列名列表
        
    Returns:
        字典列表
    """
    data = []
    for row in rows:
        row_dict = {}
        for col, val in zip(columns, row):
            # 处理None
            if val is None:
                row_dict[col] = None
            # 处理datetime类型
            elif hasattr(val, 'isoformat'):
                row_dict[col] = val.isoformat()
            # 处理UUID类型（PostgreSQL等）
            elif hasattr(val, '__class__') and 'UUID' in str(type(val)):
                row_dict[col] = str(val)
            # 处理decimal类型
            elif hasattr(val, '__float__'):
                try:
                    row_dict[col] = float(val)
                except (ValueError, TypeError):
                    row_dict[col] = str(val)
            # 处理bytes类型
            elif isinstance(val, bytes):
                try:
                    # 尝试解码为UTF-8字符串
                    row_dict[col] = val.decode('utf-8')
                except:
                    # 如果解码失败，转换为base64
                    import base64
                    row_dict[col] = base64.b64encode(val).decode('utf-8')
            # 其他类型转换为字符串（确保可序列化）
            else:
                try:
                    # 尝试直接使用（测试是否可序列化）
                    import json
                    json.dumps(val)  # 测试是否可序列化
                    row_dict[col] = val
                except (TypeError, ValueError):
                    # 如果不可序列化，转换为字符串
                    row_dict[col] = str(val)
        data.append(row_dict)
    
    return data
