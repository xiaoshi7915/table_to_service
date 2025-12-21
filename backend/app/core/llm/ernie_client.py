"""
百度文心（ERNIE）LLM客户端
使用百度智能云千帆大模型平台
"""
from typing import List, Dict, Any, Optional
import aiohttp
from loguru import logger
from app.core.llm.base import BaseLLMClient


class ErnieClient(BaseLLMClient):
    """百度文心LLM客户端"""
    
    def __init__(self, api_key: str, api_base_url: Optional[str] = None, model_name: str = "ERNIE-4.0-8K", **kwargs):
        """
        初始化百度文心客户端
        
        Args:
            api_key: 百度千帆API Key（格式：access_key:secret_key 或 access_token）
            api_base_url: API基础URL（默认：https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat）
            model_name: 模型名称（默认：ERNIE-4.0-8K）
        """
        super().__init__(api_key, api_base_url, model_name, **kwargs)
        
        # 百度千帆的默认API地址
        self.api_base_url = api_base_url or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"
        
        # 解析API密钥（可能是access_key:secret_key格式或access_token）
        self.access_token = None
        if ":" in api_key:
            # 如果是access_key:secret_key格式，需要先获取access_token
            parts = api_key.split(":", 1)
            self.api_key = parts[0]
            self.secret_key = parts[1]
        else:
            # 直接使用access_token
            self.access_token = api_key
            self.api_key = None
            self.secret_key = None
        
        # 支持的模型列表
        self.supported_models = [
            "ERNIE-4.0-8K",
            "ERNIE-4.0-8K-0205",
            "ERNIE-3.5-8K",
            "ERNIE-3.5-8K-0205",
            "ERNIE-Speed-8K",
            "ERNIE-Speed-128K"
        ]
        
        # 如果模型名称不在支持列表中，使用默认模型
        if model_name not in self.supported_models:
            logger.warning("模型 %s 可能不受支持，使用默认模型 ERNIE-4.0-8K", model_name)
            self.model_name = "ERNIE-4.0-8K"
    
    async def _get_access_token(self) -> str:
        """
        获取access_token（如果使用api_key:secret_key格式）
        
        Returns:
            access_token字符串
        """
        if self.access_token:
            return self.access_token
        
        # 使用api_key和secret_key获取access_token
        token_url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    return self.access_token
                else:
                    error_text = await response.text()
                    raise ValueError(f"获取access_token失败: {error_text}")
    
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
            # 获取access_token
            access_token = await self._get_access_token()
            
            # 预处理消息
            processed_messages = self._prepare_messages(messages)
            
            # 转换消息格式为百度千帆格式
            # 百度千帆使用messages数组，格式与OpenAI类似
            qianfan_messages = []
            for msg in processed_messages:
                qianfan_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 构建请求URL
            url = f"{self.api_base_url}/{self.model_name}"
            params = {"access_token": access_token}
            
            # 构建请求体
            request_body = {
                "messages": qianfan_messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_output_tokens": max_tokens if max_tokens is not None else self.max_tokens,
                **kwargs
            }
            
            # 调用API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params, json=request_body) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"百度文心API调用失败: HTTP {response.status}, {error_text}")
                    
                    result = await response.json()
                    
                    # 检查错误
                    if "error_code" in result:
                        error_msg = result.get("error_msg", "未知错误")
                        raise ValueError(f"百度文心API错误: {error_msg}")
                    
                    # 提取响应内容
                    content = result.get("result", "")
                    tokens_used = result.get("usage", {}).get("total_tokens") if "usage" in result else None
                    
                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "model": self.model_name
                    }
                    
        except Exception as e:
            logger.error("百度文心API调用失败: %s", str(e), exc_info=True)
            raise ValueError(f"百度文心API调用失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量（百度文心使用简单估算）
        """
        # 百度文心的token计算：中文约1.5字符=1token，英文约4字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
