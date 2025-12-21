"""
MiniMax LLM客户端
使用MiniMax开放平台API
"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger
from app.core.llm.base import BaseLLMClient
import tiktoken


class MiniMaxClient(BaseLLMClient):
    """MiniMax LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "abab6.5", **kwargs):
        """
        初始化MiniMax客户端
        
        Args:
            api_key: MiniMax API密钥
            api_base_url: API基础URL（默认：https://api.minimax.chat/v1）
            model_name: 模型名称（默认：abab6.5）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # MiniMax的默认API地址
        self.api_base_url = api_base_url or "https://api.minimax.chat/v1"
        
        # 创建OpenAI客户端（MiniMax兼容OpenAI格式）
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.api_base_url
        )
        
        # 支持的模型列表
        self.supported_models = [
            "abab6.5",
            "abab6",
            "abab5.5"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 abab6.5", model_name)
            self.model_name = "abab6.5"
        
        # 初始化token编码器
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("初始化tiktoken编码器失败: %s，将使用简单估算", str(e))
            self.encoding = None
    
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
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            响应字典
        """
        try:
            # 预处理消息
            processed_messages = self._prepare_messages(messages)
            
            # 调用API（OpenAI兼容格式）
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=processed_messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs
            )
            
            # 提取响应内容
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, "usage") else None
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model": self.model_name
            }
            
        except Exception as e:
            logger.error("MiniMax API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"MiniMax API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量
        """
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.warning("Token计数失败: %s", str(e))
        
        # 简单估算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
