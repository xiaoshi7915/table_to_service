"""
Kimi LLM客户端
Kimi使用OpenAI兼容的API格式
"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger
from app.core.llm.base import BaseLLMClient
import tiktoken


class KimiClient(BaseLLMClient):
    """Kimi LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "moonshot-v1-8k", **kwargs):
        """
        初始化Kimi客户端
        
        Args:
            api_key: Kimi API密钥
            api_base_url: API基础URL（默认：https://api.moonshot.cn）
            model_name: 模型名称（默认：moonshot-v1-8k）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # Kimi的默认API地址
        self.api_base_url = api_base_url or "https://api.moonshot.cn"
        
        # 创建OpenAI客户端（Kimi兼容OpenAI格式）
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.api_base_url
        )
        
        # 初始化token编码器
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"初始化tiktoken编码器失败: {e}，将使用简单估算")
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
            
            # 调用API
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
            logger.error(f"Kimi API调用失败: {e}", exc_info=True)
            raise ValueError(f"Kimi API调用失败: {str(e)}")
    
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
                logger.warning(f"Token计数失败: {e}")
        
        # 简单估算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


