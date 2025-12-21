"""
腾讯混元（Hunyuan）LLM客户端
使用腾讯云混元大模型API
"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import hmac
import hashlib
import time
from urllib.parse import urlencode
from loguru import logger
from app.core.llm.base import BaseLLMClient


class HunyuanClient(BaseLLMClient):
    """腾讯混元LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "hunyuan-pro", **kwargs):
        """
        初始化腾讯混元客户端
        
        Args:
            api_key: 腾讯云API密钥（格式：secret_id:secret_key）
            api_base_url: API基础URL（默认：https://hunyuan.tencentcloudapi.com）
            model_name: 模型名称（默认：hunyuan-pro）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 解析API密钥（格式：secret_id:secret_key）
        if ":" in api_key:
            parts = api_key.split(":", 1)
            self.secret_id = parts[0]
            self.secret_key = parts[1]
        else:
            raise ValueError("腾讯混元API密钥格式错误，应为 secret_id:secret_key")
        
        # 腾讯混元的默认API地址
        self.api_base_url = api_base_url or "https://hunyuan.tencentcloudapi.com"
        
        # 支持的模型列表
        self.supported_models = [
            "hunyuan-pro",
            "hunyuan-standard",
            "hunyuan-lite"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 hunyuan-pro", model_name)
            self.model_name = "hunyuan-pro"
    
    def _generate_signature(self, method: str, endpoint: str, params: dict, headers: dict) -> str:
        """
        生成腾讯云API签名
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: 请求参数
            headers: 请求头
            
        Returns:
            签名字符串
        """
        # 腾讯云签名算法（简化版，实际可能需要更复杂的实现）
        # 这里使用简化的签名方法
        timestamp = str(int(time.time()))
        nonce = str(int(time.time() * 1000))
        
        # 构建签名字符串
        sign_str = f"{method}\n{endpoint}\n{urlencode(sorted(params.items()))}\n{timestamp}\n{nonce}"
        
        # 使用HMAC-SHA256签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
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
            
            # 转换消息格式为腾讯云格式
            hunyuan_messages = []
            for msg in processed_messages:
                hunyuan_messages.append({
                    "Role": msg["role"],
                    "Content": msg["content"]
                })
            
            # 构建请求体
            request_body = {
                "Model": self.model_name,
                "Messages": hunyuan_messages,
                "Temperature": temperature if temperature is not None else self.temperature,
                "MaxTokens": max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs
            }
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "X-TC-Action": "ChatCompletions",
                "X-TC-Version": "2023-09-01",
                "X-TC-Timestamp": str(int(time.time())),
                "X-TC-SecretId": self.secret_id
            }
            
            # 调用API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_base_url,
                    json=request_body,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"腾讯混元API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "Response" in result and "Error" in result["Response"]:
                        error = result["Response"]["Error"]
                        error_msg = error.get("Message", "未知错误")
                        raise ValueError(f"腾讯混元API错误: {error_msg}")
                    
                    # 提取响应内容
                    response_data = result.get("Response", {})
                    choices = response_data.get("Choices", [])
                    if choices:
                        content = choices[0].get("Message", {}).get("Content", "")
                    else:
                        content = ""
                    
                    usage = response_data.get("Usage", {})
                    tokens_used = usage.get("TotalTokens") if usage else None
                    
                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "model": self.model_name
                    }
                    
        except Exception as e:
            logger.error("腾讯混元API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"腾讯混元API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（腾讯混元使用简单估算）
        """
        # 腾讯混元的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
