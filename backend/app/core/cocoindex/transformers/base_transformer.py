"""
基础转换器
定义所有转换器的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from loguru import logger


class BaseTransformer(ABC):
    """数据转换器基类"""
    
    def __init__(self, embedding_service=None):
        """
        初始化转换器
        
        Args:
            embedding_service: 嵌入服务（用于生成向量）
        """
        self.embedding_service = embedding_service
    
    @abstractmethod
    def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        转换数据为 Document 格式
        
        Args:
            data: 原始数据
            
        Returns:
            Document 列表，每个 Document 包含：
            {
                "content": str,  # 文档内容
                "metadata": dict,  # 元数据
                "embedding": list,  # 向量（可选）
            }
        """
        pass
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        生成文本向量
        
        Args:
            text: 文本内容
            
        Returns:
            向量列表，如果嵌入服务不可用则返回 None
        """
        if not self.embedding_service:
            return None
        
        try:
            return self.embedding_service.generate_embedding(text)
        except Exception as e:
            logger.warning(f"生成向量失败: {e}")
            return None

