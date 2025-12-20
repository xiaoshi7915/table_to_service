"""
LLM工厂类
根据配置动态创建LLM客户端实例
"""
from typing import Optional
from loguru import logger
from app.core.llm.base import BaseLLMClient
from app.core.llm.deepseek_client import DeepSeekClient
from app.core.llm.qwen_client import QwenClient
from app.core.llm.kimi_client import KimiClient
from app.models import AIModelConfig
from app.core.password_encryption import decrypt_password


class LLMFactory:
    """LLM工厂类"""
    
    # 支持的提供商映射
    PROVIDER_CLIENT_MAP = {
        "deepseek": DeepSeekClient,
        "qwen": QwenClient,
        "kimi": KimiClient,
        # 可以继续添加其他提供商
    }
    
    @classmethod
    def create_client(cls, model_config: AIModelConfig) -> BaseLLMClient:
        """
        根据模型配置创建LLM客户端
        
        Args:
            model_config: AI模型配置对象
            
        Returns:
            LLM客户端实例
        """
        provider = model_config.provider.lower()
        
        if provider not in cls.PROVIDER_CLIENT_MAP:
            raise ValueError(f"不支持的LLM提供商: {provider}，支持的提供商: {list(cls.PROVIDER_CLIENT_MAP.keys())}")
        
        # 解密API密钥
        try:
            api_key = decrypt_password(model_config.api_key)
        except Exception as e:
            logger.error("解密API密钥失败: %s", str(e))
            # 如果解密失败，尝试直接使用（可能是明文存储）
            api_key = model_config.api_key
        
        # 获取客户端类
        client_class = cls.PROVIDER_CLIENT_MAP[provider]
        
        # 创建客户端实例
        client = client_class(
            api_key=api_key,
            api_base_url=model_config.api_base_url,
            model_name=model_config.model_name,
            max_tokens=model_config.max_tokens,
            temperature=float(model_config.temperature) if isinstance(model_config.temperature, str) else model_config.temperature
        )
        
        return client
    
    @classmethod
    def create_client_by_provider(
        cls,
        provider: str,
        api_key: str,
        api_base_url: Optional[str] = None,
        model_name: str = "",
        **kwargs
    ) -> BaseLLMClient:
        """
        直接根据提供商创建客户端（用于测试等场景）
        
        Args:
            provider: 提供商名称（deepseek, qwen, kimi等）
            api_key: API密钥
            api_base_url: API基础URL
            model_name: 模型名称
            **kwargs: 其他参数
            
        Returns:
            LLM客户端实例
        """
        provider = provider.lower()
        
        if provider not in cls.PROVIDER_CLIENT_MAP:
            raise ValueError(f"不支持的LLM提供商: {provider}")
        
        client_class = cls.PROVIDER_CLIENT_MAP[provider]
        
        # 根据提供商设置默认模型名称
        if not model_name:
            default_models = {
                "deepseek": "deepseek-chat",
                "qwen": "qwen-turbo",
                "kimi": "moonshot-v1-8k"
            }
            model_name = default_models.get(provider, "")
        
        # 根据提供商设置默认API地址
        if not api_base_url:
            default_urls = {
                "deepseek": "https://api.deepseek.com",
                "qwen": None,  # DashScope不需要base_url
                "kimi": "https://api.moonshot.cn"
            }
            api_base_url = default_urls.get(provider)
        
        client = client_class(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            **kwargs
        )
        
        return client
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """
        获取支持的提供商列表
        
        Returns:
            提供商列表
        """
        return list(cls.PROVIDER_CLIENT_MAP.keys())


