"""
中文嵌入服务
使用 bge-base-zh-v1.5 模型（BAAI General Embedding）
"""
from typing import List, Optional
import os
import threading
try:
    # LangChain 1.x
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.embeddings import Embeddings
except ImportError:
    # LangChain 0.x (fallback)
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.embeddings.base import Embeddings
from loguru import logger

# 配置 Hugging Face 镜像源（如果未设置环境变量）
if not os.getenv("HF_ENDPOINT"):
    # 优先使用 .env 文件中的配置，如果没有则使用国内镜像
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    logger.info("设置 Hugging Face 镜像源: https://hf-mirror.com")


# 全局嵌入服务实例（单例模式，避免重复加载模型）
_embedding_service_instance: Optional['ChineseEmbeddingService'] = None
_embedding_service_lock = threading.Lock()

class ChineseEmbeddingService:
    """中文嵌入服务（使用bge-base-zh-v1.5）"""
    
    def __init__(self, model_name: str = "BAAI/bge-base-zh-v1.5", force_reload: bool = False):
        """
        初始化中文嵌入服务（单例模式，避免重复加载模型）
        
        Args:
            model_name: 模型名称，默认使用BAAI/bge-base-zh-v1.5
            force_reload: 是否强制重新加载（默认False，使用单例）
        """
        self.model_name = model_name
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={
                    'normalize_embeddings': True,  # 归一化向量
                    'batch_size': 32  # 批量处理大小
                }
            )
            logger.info(f"成功加载中文嵌入模型: {model_name}")
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_instance(cls, model_name: str = "BAAI/bge-base-zh-v1.5", force_reload: bool = False) -> 'ChineseEmbeddingService':
        """
        获取嵌入服务单例实例（避免重复加载模型，提升性能）
        
        Args:
            model_name: 模型名称
            force_reload: 是否强制重新加载
            
        Returns:
            嵌入服务实例
        """
        global _embedding_service_instance, _embedding_service_lock
        
        if force_reload or _embedding_service_instance is None:
            if _embedding_service_lock:
                with _embedding_service_lock:
                    if force_reload or _embedding_service_instance is None:
                        _embedding_service_instance = cls(model_name=model_name)
            else:
                if force_reload or _embedding_service_instance is None:
                    _embedding_service_instance = cls(model_name=model_name)
        
        return _embedding_service_instance
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文档嵌入向量
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"生成文档嵌入向量失败: {e}", exc_info=True)
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        生成查询嵌入向量
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"生成查询嵌入向量失败: {e}", exc_info=True)
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            向量维度（bge-base-zh-v1.5为768）
        """
        # bge-base-zh-v1.5的维度是768
        return 768


