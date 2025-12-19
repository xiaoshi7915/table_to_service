"""
中文嵌入服务
使用 text2vec-base-chinese 模型
"""
from typing import List
try:
    # LangChain 1.x
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.embeddings import Embeddings
except ImportError:
    # LangChain 0.x (fallback)
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.embeddings.base import Embeddings
from loguru import logger


class ChineseEmbeddingService:
    """中文嵌入服务（使用text2vec-base-chinese）"""
    
    def __init__(self, model_name: str = "text2vec-base-chinese"):
        """
        初始化中文嵌入服务
        
        Args:
            model_name: 模型名称，默认使用text2vec-base-chinese
        """
        self.model_name = model_name
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}  # 归一化向量
            )
            logger.info(f"成功加载中文嵌入模型: {model_name}")
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}", exc_info=True)
            raise
    
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
            向量维度（text2vec-base-chinese为768）
        """
        # text2vec-base-chinese的维度是768
        return 768


