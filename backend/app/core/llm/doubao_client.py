"""
字节豆包（Doubao）LLM客户端
使用火山引擎豆包大模型API
"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
from loguru import logger
from app.core.llm.base import BaseLLMClient


class DoubaoClient(BaseLLMClient):
    """字节豆包LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "doubao-pro-4k", **kwargs):
        """
        初始化字节豆包客户端
        
        Args:
            api_key: 火山引擎API密钥（格式：access_key_id:secret_access_key 或 token）
            api_base_url: API基础URL（默认：https://ark.cn-beijing.volces.com/api/v3）
            model_name: 模型名称（默认：doubao-pro-4k）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 火山引擎的默认API地址
        self.api_base_url = api_base_url or "https://ark.cn-beijing.volces.com/api/v3"
        
        # 解析API密钥
        self.api_key = api_key
        if ":" in api_key:
            parts = api_key.split(":", 1)
            self.access_key_id = parts[0]
            self.secret_access_key = parts[1]
        else:
            # 直接使用token
            self.access_key_id = None
            self.secret_access_key = None
        
        # 支持的模型列表
        self.supported_models = [
            "doubao-pro-4k",
            "doubao-lite-4k",
            "doubao-pro-32k",
            "doubao-lite-32k"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 doubao-pro-4k", model_name)
            self.model_name = "doubao-pro-4k"
    
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
            
            # 转换消息格式为火山引擎格式（OpenAI兼容）
            doubao_messages = []
            for msg in processed_messages:
                doubao_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 构建请求体
            request_body = {
                "model": self.model_name,
                "messages": doubao_messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs
            }
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 调用API
            url = f"{self.api_base_url}/chat/completions"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_body, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"字节豆包API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "error" in result:
                        error = result["error"]
                        error_msg = error.get("message", "未知错误")
                        raise ValueError(f"字节豆包API错误: {error_msg}")
                    
                    # 提取响应内容（OpenAI兼容格式）
                    choices = result.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                    else:
                        content = ""
                    
                    usage = result.get("usage", {})
                    tokens_used = usage.get("total_tokens") if usage else None
                    
                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "model": self.model_name
                    }
                    
        except Exception as e:
            logger.error("字节豆包API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"字节豆包API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（字节豆包使用简单估算）
        """
        # 字节豆包的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
