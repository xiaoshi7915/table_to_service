"""
通义千问（Qwen）LLM客户端
使用阿里云DashScope SDK
"""
from typing import List, Dict, Any, Optional
import dashscope
from loguru import logger
from app.core.llm.base import BaseLLMClient


class QwenClient(BaseLLMClient):
    """通义千问LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "qwen-turbo", **kwargs):
        """
        初始化通义千问客户端
        
        Args:
            api_key: DashScope API密钥
            api_base_url: API基础URL（DashScope不需要，但保留参数兼容性）
            model_name: 模型名称（默认：qwen-turbo）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 设置DashScope API密钥
        dashscope.api_key = api_key
        
        # 支持的模型列表
        self.supported_models = [
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "qwen-max-longcontext"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 qwen-turbo", model_name)
            self.model_name = "qwen-turbo"
    
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
            
            # 转换消息格式为DashScope格式
            dashscope_messages = []
            for msg in processed_messages:
                dashscope_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 调用DashScope API
            response = dashscope.Generation.call(
                model=self.model_name,
                messages=dashscope_messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = response.message if hasattr(response, "message") else "未知错误"
                raise ValueError(f"DashScope API调用失败: {error_msg}")
            
            # 提取响应内容
            content = response.output.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, "usage") else None
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "model": self.model_name
            }
            
        except Exception as e:
            # 使用 %s 格式化避免 loguru 解析错误消息中的 {error} 等占位符
            logger.error("通义千问API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"通义千问API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（通义千问使用简单估算）
        """
        # 通义千问的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


