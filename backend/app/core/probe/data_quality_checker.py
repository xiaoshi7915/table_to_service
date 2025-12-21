"""
数据质量检测器
检测数据格式合规性、范围合规性、参照合规性等
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger


class DataQualityChecker:
    """数据质量检测器"""
    
    # 邮箱正则表达式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # 手机号正则表达式（中国大陆）
    PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')
    
    # 身份证号正则表达式（18位）
    ID_CARD_PATTERN = re.compile(r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$')
    
    # 银行卡号正则表达式（16-19位数字）
    BANK_CARD_PATTERN = re.compile(r'^\d{16,19}$')
    
    # IP地址正则表达式
    IP_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    
    # MAC地址正则表达式
    MAC_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    
    @staticmethod
    def check_format_compliance(value: Any, format_type: str) -> bool:
        """
        检查格式合规性
        
        Args:
            value: 待检查的值
            format_type: 格式类型（email, phone, id_card, bank_card, ip, mac等）
            
        Returns:
            是否符合格式
        """
        if value is None:
            return False
        
        value_str = str(value).strip()
        
        if format_type == "email":
            return bool(DataQualityChecker.EMAIL_PATTERN.match(value_str))
        elif format_type == "phone":
            return bool(DataQualityChecker.PHONE_PATTERN.match(value_str))
        elif format_type == "id_card":
            return bool(DataQualityChecker.ID_CARD_PATTERN.match(value_str))
        elif format_type == "bank_card":
            return bool(DataQualityChecker.BANK_CARD_PATTERN.match(value_str))
        elif format_type == "ip":
            return bool(DataQualityChecker.IP_PATTERN.match(value_str))
        elif format_type == "mac":
            return bool(DataQualityChecker.MAC_PATTERN.match(value_str))
        else:
            return False
    
    @staticmethod
    def check_range_compliance(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> bool:
        """
        检查范围合规性
        
        Args:
            value: 待检查的值
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            是否在范围内
        """
        if value is None:
            return False
        
        try:
            num_value = float(value)
            if min_value is not None and num_value < min_value:
                return False
            if max_value is not None and num_value > max_value:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def check_reference_compliance(value: Any, reference_set: set) -> bool:
        """
        检查参照合规性（值是否在参考集合中）
        
        Args:
            value: 待检查的值
            reference_set: 参考集合
            
        Returns:
            是否在参考集合中
        """
        if value is None:
            return False
        return value in reference_set
    
    @staticmethod
    def detect_format_issues(sample_values: List[Any], column_name: str) -> List[Dict[str, Any]]:
        """
        检测格式问题
        
        Args:
            sample_values: 样本值列表
            column_name: 字段名
            
        Returns:
            格式问题列表
        """
        issues = []
        
        # 检测邮箱格式
        email_count = sum(1 for v in sample_values if DataQualityChecker.check_format_compliance(v, "email"))
        if email_count > len(sample_values) * 0.8:  # 80%以上符合邮箱格式
            issues.append({
                "type": "format",
                "format_type": "email",
                "description": f"字段 {column_name} 可能包含邮箱地址",
                "compliance_rate": email_count / len(sample_values) if sample_values else 0
            })
        
        # 检测手机号格式
        phone_count = sum(1 for v in sample_values if DataQualityChecker.check_format_compliance(v, "phone"))
        if phone_count > len(sample_values) * 0.8:
            issues.append({
                "type": "format",
                "format_type": "phone",
                "description": f"字段 {column_name} 可能包含手机号",
                "compliance_rate": phone_count / len(sample_values) if sample_values else 0
            })
        
        # 检测身份证号格式
        id_card_count = sum(1 for v in sample_values if DataQualityChecker.check_format_compliance(v, "id_card"))
        if id_card_count > len(sample_values) * 0.8:
            issues.append({
                "type": "format",
                "format_type": "id_card",
                "description": f"字段 {column_name} 可能包含身份证号",
                "compliance_rate": id_card_count / len(sample_values) if sample_values else 0
            })
        
        return issues
    
    @staticmethod
    def detect_range_issues(values: List[Any], column_name: str, expected_min: Optional[float] = None, expected_max: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        检测范围问题
        
        Args:
            values: 值列表
            column_name: 字段名
            expected_min: 期望的最小值
            expected_max: 期望的最大值
            
        Returns:
            范围问题列表
        """
        issues = []
        
        if not values:
            return issues
        
        numeric_values = []
        for v in values:
            try:
                if v is not None:
                    numeric_values.append(float(v))
            except (ValueError, TypeError):
                continue
        
        if not numeric_values:
            return issues
        
        actual_min = min(numeric_values)
        actual_max = max(numeric_values)
        
        if expected_min is not None and actual_min < expected_min:
            issues.append({
                "type": "range",
                "description": f"字段 {column_name} 的最小值 {actual_min} 小于期望值 {expected_min}",
                "actual_min": actual_min,
                "expected_min": expected_min
            })
        
        if expected_max is not None and actual_max > expected_max:
            issues.append({
                "type": "range",
                "description": f"字段 {column_name} 的最大值 {actual_max} 大于期望值 {expected_max}",
                "actual_max": actual_max,
                "expected_max": expected_max
            })
        
        return issues

