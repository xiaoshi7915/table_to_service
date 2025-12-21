"""
科大讯飞星火（Spark）LLM客户端
使用讯飞开放平台API
"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import hmac
import hashlib
import base64
from urllib.parse import urlencode, urlparse
from datetime import datetime
from loguru import logger
from app.core.llm.base import BaseLLMClient


class SparkClient(BaseLLMClient):
    """科大讯飞星火LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "Spark-4.0-Ultra", **kwargs):
        """
        初始化科大讯飞星火客户端
        
        Args:
            api_key: 讯飞API密钥（格式：app_id:api_key:api_secret）
            api_base_url: API基础URL（默认：https://spark-api.xf-yun.com/v1）
            model_name: 模型名称（默认：Spark-4.0-Ultra）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 解析API密钥（格式：app_id:api_key:api_secret）
        if api_key.count(":") == 2:
            parts = api_key.split(":", 2)
            self.app_id = parts[0]
            self.api_key_part = parts[1]
            self.api_secret = parts[2]
        else:
            raise ValueError("科大讯飞星火API密钥格式错误，应为 app_id:api_key:api_secret")
        
        # 讯飞星火的默认API地址
        self.api_base_url = api_base_url or "https://spark-api.xf-yun.com/v1"
        
        # 支持的模型列表
        self.supported_models = [
            "Spark-4.0-Ultra",
            "Spark-3.5-Max",
            "Spark-3.5-Pro",
            "Spark-3.1"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 Spark-4.0-Ultra", model_name)
            self.model_name = "Spark-4.0-Ultra"
    
    def _generate_auth_url(self, host: str, path: str) -> str:
        """
        生成讯飞API认证URL
        
        Args:
            host: 主机名
            path: 路径
            
        Returns:
            带认证参数的URL
        """
        # 生成时间戳
        now = datetime.now()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 构建签名字符串
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        
        # 使用HMAC-SHA256签名
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
        
        # 构建authorization字符串
        authorization_origin = f'api_key="{self.api_key_part}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        # 构建URL参数
        params = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        
        return f"https://{host}{path}?{urlencode(params)}"
    
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
            
            # 转换消息格式为讯飞格式
            spark_messages = []
            for msg in processed_messages:
                spark_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 构建请求体
            request_body = {
                "header": {
                    "app_id": self.app_id,
                    "uid": "fd3f47e4-d"
                },
                "parameter": {
                    "chat": {
                        "domain": self.model_name.lower().replace("-", "_"),
                        "temperature": temperature if temperature is not None else self.temperature,
                        "max_tokens": max_tokens if max_tokens is not None else self.max_tokens
                    }
                },
                "payload": {
                    "message": {
                        "text": spark_messages
                    }
                }
            }
            
            # 解析API URL
            parsed_url = urlparse(self.api_base_url)
            host = parsed_url.netloc
            path = parsed_url.path or "/chat/completions"
            
            # 生成认证URL
            auth_url = self._generate_auth_url(host, path)
            
            # 调用API
            async with aiohttp.ClientSession() as session:
                async with session.post(auth_url, json=request_body) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"科大讯飞星火API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "header" in result and result["header"]["code"] != 0:
                        error_msg = result["header"].get("message", "未知错误")
                        raise ValueError(f"科大讯飞星火API错误: {error_msg}")
                    
                    # 提取响应内容
                    payload = result.get("payload", {})
                    choices = payload.get("choices", {})
                    text = choices.get("text", [])
                    if text:
                        content = text[0].get("content", "")
                    else:
                        content = ""
                    
                    usage = payload.get("usage", {})
                    tokens_used = usage.get("total_tokens") if usage else None
                    
                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "model": self.model_name
                    }
                    
        except Exception as e:
            logger.error("科大讯飞星火API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"科大讯飞星火API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（科大讯飞星火使用简单估算）
        """
        # 科大讯飞星火的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

