"""
敏感信息检测器
检测敏感数据（身份证、银行卡、手机号、邮箱等）
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger


class SensitiveInfoDetector:
    """敏感信息检测器"""
    
    # 身份证号正则表达式
    ID_CARD_PATTERN = re.compile(r'[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]')
    
    # 银行卡号正则表达式（16-19位数字）
    BANK_CARD_PATTERN = re.compile(r'\b\d{16,19}\b')
    
    # 手机号正则表达式（中国大陆）
    PHONE_PATTERN = re.compile(r'\b1[3-9]\d{9}\b')
    
    # 邮箱正则表达式
    EMAIL_PATTERN = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
    
    # IP地址正则表达式
    IP_PATTERN = re.compile(r'\b(\d{1,3}\.){3}\d{1,3}\b')
    
    # MAC地址正则表达式
    MAC_PATTERN = re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b')
    
    # 敏感关键字
    SENSITIVE_KEYWORDS = [
        "password", "passwd", "pwd", "secret", "token", "key",
        "身份证", "身份证号", "身份证号码",
        "银行卡", "银行卡号", "卡号",
        "手机号", "手机", "电话", "电话号",
        "邮箱", "email", "mail",
        "密码", "密钥", "token", "secret"
    ]
    
    @staticmethod
    def detect_sensitive_data(value: Any, column_name: str = "") -> Dict[str, Any]:
        """
        检测敏感数据
        
        Args:
            value: 待检测的值
            column_name: 字段名（用于关键字匹配）
            
        Returns:
            敏感信息检测结果
        """
        if value is None:
            return {
                "is_sensitive": False,
                "sensitive_types": [],
                "confidence": 0.0
            }
        
        value_str = str(value)
        column_name_lower = column_name.lower()
        
        sensitive_types = []
        confidence = 0.0
        
        # 检查字段名是否包含敏感关键字
        is_sensitive_column = any(keyword in column_name_lower for keyword in SensitiveInfoDetector.SENSITIVE_KEYWORDS)
        
        # 检测身份证号
        if SensitiveInfoDetector.ID_CARD_PATTERN.search(value_str):
            sensitive_types.append("id_card")
            confidence = 0.9
        
        # 检测银行卡号
        if SensitiveInfoDetector.BANK_CARD_PATTERN.search(value_str):
            sensitive_types.append("bank_card")
            confidence = max(confidence, 0.8)
        
        # 检测手机号
        if SensitiveInfoDetector.PHONE_PATTERN.search(value_str):
            sensitive_types.append("phone")
            confidence = max(confidence, 0.7)
        
        # 检测邮箱
        if SensitiveInfoDetector.EMAIL_PATTERN.search(value_str):
            sensitive_types.append("email")
            confidence = max(confidence, 0.6)
        
        # 检测IP地址
        if SensitiveInfoDetector.IP_PATTERN.search(value_str):
            sensitive_types.append("ip")
            confidence = max(confidence, 0.5)
        
        # 检测MAC地址
        if SensitiveInfoDetector.MAC_PATTERN.search(value_str):
            sensitive_types.append("mac")
            confidence = max(confidence, 0.5)
        
        # 如果字段名包含敏感关键字，提高置信度
        if is_sensitive_column and sensitive_types:
            confidence = min(confidence + 0.2, 1.0)
        elif is_sensitive_column:
            sensitive_types.append("sensitive_column_name")
            confidence = 0.5
        
        return {
            "is_sensitive": len(sensitive_types) > 0,
            "sensitive_types": sensitive_types,
            "confidence": confidence,
            "column_name_sensitive": is_sensitive_column
        }
    
    @staticmethod
    def scan_with_regex(text: str, pattern: re.Pattern) -> List[str]:
        """
        使用正则表达式扫描文本
        
        Args:
            text: 待扫描的文本
            pattern: 正则表达式模式
            
        Returns:
            匹配结果列表
        """
        matches = pattern.findall(text)
        return matches if isinstance(matches[0], str) else [m[0] if isinstance(m, tuple) else str(m) for m in matches]
    
    @staticmethod
    def scan_with_keywords(text: str, keywords: Optional[List[str]] = None) -> List[str]:
        """
        使用关键字扫描文本
        
        Args:
            text: 待扫描的文本
            keywords: 关键字列表（如果为None，使用默认敏感关键字）
            
        Returns:
            匹配的关键字列表
        """
        if keywords is None:
            keywords = SensitiveInfoDetector.SENSITIVE_KEYWORDS
        
        text_lower = text.lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
        return matched_keywords
    
    @staticmethod
    def detect_in_column(column_name: str, sample_values: List[Any]) -> Dict[str, Any]:
        """
        检测字段中的敏感信息
        
        Args:
            column_name: 字段名
            sample_values: 样本值列表
            
        Returns:
            敏感信息检测结果
        """
        # 检查字段名
        column_detection = SensitiveInfoDetector.detect_sensitive_data(column_name, column_name)
        
        # 检查样本值
        value_detections = []
        for value in sample_values[:100]:  # 只检查前100个样本
            detection = SensitiveInfoDetector.detect_sensitive_data(value, column_name)
            if detection["is_sensitive"]:
                value_detections.append(detection)
        
        # 汇总结果
        all_sensitive_types = set(column_detection.get("sensitive_types", []))
        max_confidence = column_detection.get("confidence", 0.0)
        
        for detection in value_detections:
            all_sensitive_types.update(detection.get("sensitive_types", []))
            max_confidence = max(max_confidence, detection.get("confidence", 0.0))
        
        # 如果样本值中有敏感信息，提高置信度
        if value_detections:
            max_confidence = min(max_confidence + 0.1, 1.0)
        
        return {
            "is_sensitive": len(all_sensitive_types) > 0,
            "sensitive_types": list(all_sensitive_types),
            "confidence": max_confidence,
            "sample_count": len(sample_values),
            "sensitive_sample_count": len(value_detections)
        }

