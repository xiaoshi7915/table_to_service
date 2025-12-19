"""
LLM客户端抽象基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "", **kwargs):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥
            api_base_url: API基础URL（可选）
            model_name: 模型名称
            **kwargs: 其他参数
        """
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model_name = model_name
        self.max_tokens = kwargs.get("max_tokens", 2000)
        self.temperature = float(kwargs.get("temperature", 0.7))
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天补全请求
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大token数（可选，覆盖默认值）
            **kwargs: 其他参数
            
        Returns:
            包含响应内容的字典，格式：{
                "content": "响应内容",
                "tokens_used": 使用的token数,
                "model": "模型名称"
            }
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量
        """
        pass
    
    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        预处理消息列表
        
        Args:
            messages: 原始消息列表
            
        Returns:
            处理后的消息列表
        """
        # 确保消息格式正确
        processed = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                processed.append({
                    "role": msg["role"],
                    "content": str(msg["content"])
                })
            else:
                logger.warning(f"跳过无效消息: {msg}")
        return processed


