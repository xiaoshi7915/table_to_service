"""
昆仑万维Skywork LLM客户端
使用昆仑万维开放平台API
"""
from typing import List, Dict, Any, Optional
import aiohttp
from loguru import logger
from app.core.llm.base import BaseLLMClient


class SkyworkClient(BaseLLMClient):
    """昆仑万维Skywork LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "skywork-13b-chat", **kwargs):
        """
        初始化昆仑万维Skywork客户端
        
        Args:
            api_key: 昆仑万维API密钥
            api_base_url: API基础URL（默认：https://api.skywork.ai/v1）
            model_name: 模型名称（默认：skywork-13b-chat）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 昆仑万维的默认API地址
        self.api_base_url = api_base_url or "https://api.skywork.ai/v1"
        
        # 支持的模型列表
        self.supported_models = [
            "skywork-13b-chat",
            "skywork-6b-chat"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 skywork-13b-chat", model_name)
            self.model_name = "skywork-13b-chat"
    
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
            
            # 转换消息格式为昆仑万维格式（OpenAI兼容）
            skywork_messages = []
            for msg in processed_messages:
                skywork_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 构建请求体
            request_body = {
                "model": self.model_name,
                "messages": skywork_messages,
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
                        raise ValueError(f"昆仑万维Skywork API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "error" in result:
                        error = result["error"]
                        error_msg = error.get("message", "未知错误")
                        raise ValueError(f"昆仑万维Skywork API错误: {error_msg}")
                    
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
            logger.error("昆仑万维Skywork API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"昆仑万维Skywork API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（昆仑万维Skywork使用简单估算）
        """
        # 昆仑万维Skywork的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

