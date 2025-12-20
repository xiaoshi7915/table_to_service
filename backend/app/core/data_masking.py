"""
数据脱敏服务
对查询结果中的敏感信息进行脱敏处理
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger


class DataMaskingService:
    """数据脱敏服务"""
    
    # 敏感字段模式（匹配字段名）
    SENSITIVE_FIELD_PATTERNS = [
        # 身份证号
        r'id_card|idcard|身份证|identity_card',
        # 手机号
        r'phone|mobile|tel|电话|手机',
        # 邮箱
        r'email|mail|邮箱|电子邮箱',
        # 银行卡号
        r'bank_card|card_no|银行卡|卡号',
        # 密码
        r'password|pwd|passwd|密码',
        # 姓名（可能包含敏感信息）
        r'name|姓名|真实姓名',
        # 地址
        r'address|addr|地址|住址',
        # 其他敏感信息
        r'secret|token|api_key|密钥|秘钥',
    ]
    
    # 敏感数据模式（匹配数据内容）
    SENSITIVE_DATA_PATTERNS = {
        # 身份证号：18位数字，最后一位可能是X
        'id_card': r'^\d{17}[\dXx]$',
        # 手机号：11位数字，1开头
        'phone': r'^1[3-9]\d{9}$',
        # 邮箱
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        # 银行卡号：16-19位数字
        'bank_card': r'^\d{16,19}$',
    }
    
    @classmethod
    def is_sensitive_field(cls, field_name: str) -> bool:
        """
        判断字段名是否敏感
        
        Args:
            field_name: 字段名
            
        Returns:
            是否敏感
        """
        field_lower = field_name.lower()
        for pattern in cls.SENSITIVE_FIELD_PATTERNS:
            if re.search(pattern, field_lower, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def mask_value(cls, value: Any, field_name: Optional[str] = None) -> Any:
        """
        对单个值进行脱敏处理
        
        Args:
            value: 要脱敏的值
            field_name: 字段名（可选，用于判断是否敏感字段）
            
        Returns:
            脱敏后的值
        """
        if value is None:
            return value
        
        # 转换为字符串进行处理
        value_str = str(value)
        
        # 如果字段名是敏感字段，直接脱敏
        if field_name and cls.is_sensitive_field(field_name):
            return cls._mask_by_field_type(value_str, field_name)
        
        # 检查数据内容是否匹配敏感数据模式
        for data_type, pattern in cls.SENSITIVE_DATA_PATTERNS.items():
            if re.match(pattern, value_str):
                return cls._mask_by_data_type(value_str, data_type)
        
        return value
    
    @classmethod
    def _mask_by_field_type(cls, value: str, field_name: str) -> str:
        """
        根据字段类型进行脱敏
        
        Args:
            value: 原始值
            field_name: 字段名
            
        Returns:
            脱敏后的值
        """
        field_lower = field_name.lower()
        
        # 身份证号
        if re.search(r'id_card|idcard|身份证', field_lower):
            if len(value) == 18:
                return f"{value[:6]}********{value[-4:]}"
            elif len(value) >= 10:
                return f"{value[:3]}****{value[-4:]}"
            else:
                return "****"
        
        # 手机号
        if re.search(r'phone|mobile|tel|电话|手机', field_lower):
            if len(value) == 11:
                return f"{value[:3]}****{value[-4:]}"
            else:
                return "****"
        
        # 邮箱
        if re.search(r'email|mail|邮箱', field_lower):
            if '@' in value:
                parts = value.split('@')
                if len(parts) == 2:
                    username = parts[0]
                    domain = parts[1]
                    if len(username) > 2:
                        masked_username = f"{username[0]}***{username[-1]}"
                    else:
                        masked_username = "***"
                    return f"{masked_username}@{domain}"
            return "***@***"
        
        # 银行卡号
        if re.search(r'bank_card|card_no|银行卡|卡号', field_lower):
            if len(value) >= 16:
                return f"{value[:4]}****{value[-4:]}"
            else:
                return "****"
        
        # 密码
        if re.search(r'password|pwd|passwd|密码', field_lower):
            return "******"
        
        # 默认脱敏：保留前2位和后2位，中间用*替代
        if len(value) > 4:
            return f"{value[:2]}***{value[-2:]}"
        elif len(value) > 2:
            return f"{value[0]}***{value[-1]}"
        else:
            return "***"
    
    @classmethod
    def _mask_by_data_type(cls, value: str, data_type: str) -> str:
        """
        根据数据类型进行脱敏
        
        Args:
            value: 原始值
            data_type: 数据类型
            
        Returns:
            脱敏后的值
        """
        if data_type == 'id_card':
            if len(value) == 18:
                return f"{value[:6]}********{value[-4:]}"
            else:
                return "****"
        
        elif data_type == 'phone':
            if len(value) == 11:
                return f"{value[:3]}****{value[-4:]}"
            else:
                return "****"
        
        elif data_type == 'email':
            if '@' in value:
                parts = value.split('@')
                if len(parts) == 2:
                    username = parts[0]
                    domain = parts[1]
                    if len(username) > 2:
                        masked_username = f"{username[0]}***{username[-1]}"
                    else:
                        masked_username = "***"
                    return f"{masked_username}@{domain}"
            return "***@***"
        
        elif data_type == 'bank_card':
            if len(value) >= 16:
                return f"{value[:4]}****{value[-4:]}"
            else:
                return "****"
        
        return value
    
    @classmethod
    def mask_data(cls, data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        对查询结果数据进行脱敏处理
        
        Args:
            data: 查询结果数据列表
            columns: 列名列表（可选，如果不提供则从数据中提取）
            
        Returns:
            脱敏后的数据列表
        """
        if not data:
            return data
        
        # 获取列名
        if not columns:
            columns = list(data[0].keys()) if data else []
        
        # 对每条记录进行脱敏
        masked_data = []
        for row in data:
            masked_row = {}
            for col in columns:
                value = row.get(col)
                masked_row[col] = cls.mask_value(value, col)
            masked_data.append(masked_row)
        
        return masked_data
    
    @classmethod
    def should_mask(cls, field_name: str, value: Any) -> bool:
        """
        判断是否需要脱敏
        
        Args:
            field_name: 字段名
            value: 字段值
            
        Returns:
            是否需要脱敏
        """
        # 检查字段名
        if cls.is_sensitive_field(field_name):
            return True
        
        # 检查数据内容
        if value is not None:
            value_str = str(value)
            for pattern in cls.SENSITIVE_DATA_PATTERNS.values():
                if re.match(pattern, value_str):
                    return True
        
        return False
