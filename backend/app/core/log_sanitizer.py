"""
日志脱敏工具
用于在记录日志前脱敏敏感信息，防止敏感数据泄露
"""
import re
from typing import Any, Dict, List, Optional
from loguru import logger


class LogSanitizer:
    """日志脱敏工具类"""
    
    # 敏感关键词模式（用于识别需要脱敏的内容）
    SENSITIVE_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'pwd["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'passwd["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'api_key["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
        r'authorization["\']?\s*[:=]\s*["\']?([^"\',\s]+)',
    ]
    
    # SQL中的敏感模式（用于脱敏SQL语句中的敏感值）
    SQL_SENSITIVE_PATTERNS = [
        r"password\s*=\s*['\"]([^'\"]+)['\"]",
        r"pwd\s*=\s*['\"]([^'\"]+)['\"]",
        r"token\s*=\s*['\"]([^'\"]+)['\"]",
    ]
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 200) -> str:
        """
        脱敏字符串中的敏感信息
        
        Args:
            text: 要脱敏的文本
            max_length: 最大长度，超过部分会被截断
            
        Returns:
            脱敏后的文本
        """
        if not text:
            return text
        
        # 截断过长的文本
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # 脱敏敏感模式
        sanitized = text
        for pattern in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: m.group(0).replace(m.group(1), "***"),
                sanitized,
                flags=re.IGNORECASE
            )
        
        # 脱敏SQL中的敏感值
        for pattern in cls.SQL_SENSITIVE_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: m.group(0).replace(m.group(1), "***"),
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        脱敏字典中的敏感字段
        
        Args:
            data: 要脱敏的字典
            sensitive_keys: 敏感字段名列表，如果为None则使用默认列表
            
        Returns:
            脱敏后的字典
        """
        if sensitive_keys is None:
            sensitive_keys = ['password', 'pwd', 'passwd', 'token', 'api_key', 'secret', 'authorization']
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # 检查是否是敏感字段
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***"
            elif isinstance(value, str):
                # 对字符串值进行脱敏
                sanitized[key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                sanitized[key] = cls.sanitize_dict(value, sensitive_keys)
            elif isinstance(value, list):
                # 处理列表
                sanitized[key] = [
                    cls.sanitize_dict(item, sensitive_keys) if isinstance(item, dict)
                    else cls.sanitize_string(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def sanitize_sql(cls, sql: str, max_length: int = 200) -> str:
        """
        脱敏SQL语句中的敏感信息
        
        Args:
            sql: SQL语句
            max_length: 最大长度
            
        Returns:
            脱敏后的SQL语句
        """
        if not sql:
            return sql
        
        # 截断过长的SQL
        if len(sql) > max_length:
            sql = sql[:max_length] + "..."
        
        # 脱敏SQL中的敏感值
        sanitized = sql
        for pattern in cls.SQL_SENSITIVE_PATTERNS:
            sanitized = re.sub(
                pattern,
                lambda m: m.group(0).replace(m.group(1), "***"),
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized


def safe_log_sql(sql: str, max_length: int = 200) -> str:
    """
    安全记录SQL语句（脱敏敏感信息）
    
    Args:
        sql: SQL语句
        max_length: 最大记录长度
        
    Returns:
        脱敏后的SQL语句
    """
    return LogSanitizer.sanitize_sql(sql, max_length)


def safe_log_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    安全记录参数字典（脱敏敏感信息）
    
    Args:
        params: 参数字典
        
    Returns:
        脱敏后的参数字典
    """
    return LogSanitizer.sanitize_dict(params)
