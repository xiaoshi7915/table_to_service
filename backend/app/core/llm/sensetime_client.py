"""
商汤日日新（SenseNova）LLM客户端
使用商汤科技开放平台API
"""
from typing import List, Dict, Any, Optional
import aiohttp
from loguru import logger
from app.core.llm.base import BaseLLMClient


class SenseTimeClient(BaseLLMClient):
    """商汤日日新LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "SenseNova-5.5", **kwargs):
        """
        初始化商汤日日新客户端
        
        Args:
            api_key: 商汤API密钥
            api_base_url: API基础URL（默认：https://api.sensenova.cn/v1）
            model_name: 模型名称（默认：SenseNova-5.5）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 商汤的默认API地址
        self.api_base_url = api_base_url or "https://api.sensenova.cn/v1"
        
        # 支持的模型列表
        self.supported_models = [
            "SenseNova-5.5",
            "SenseChat-5",
            "SenseChat-4"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 SenseNova-5.5", model_name)
            self.model_name = "SenseNova-5.5"
    
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
            
            # 转换消息格式为商汤格式（OpenAI兼容）
            sensetime_messages = []
            for msg in processed_messages:
                sensetime_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 构建请求体
            request_body = {
                "model": self.model_name,
                "messages": sensetime_messages,
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
                        raise ValueError(f"商汤日日新API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "error" in result:
                        error = result["error"]
                        error_msg = error.get("message", "未知错误")
                        raise ValueError(f"商汤日日新API错误: {error_msg}")
                    
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
            logger.error("商汤日日新API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"商汤日日新API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（商汤日日新使用简单估算）
        """
        # 商汤日日新的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

