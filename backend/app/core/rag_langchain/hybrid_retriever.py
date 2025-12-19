"""
混合检索器
结合向量检索和关键词检索（BM25）
"""
from typing import List, Dict, Any, Optional
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.schema import Document
from langchain.vectorstores import VectorStore
from loguru import logger


class HybridRetriever:
    """混合检索器（向量检索 + 关键词检索）"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        documents: List[Document],
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        vector_k: int = 10,
        keyword_k: int = 10
    ):
        """
        初始化混合检索器
        
        Args:
            vector_store: 向量存储对象
            documents: 文档列表（用于BM25检索）
            vector_weight: 向量检索权重（0-1）
            keyword_weight: 关键词检索权重（0-1）
            vector_k: 向量检索返回数量
            keyword_k: 关键词检索返回数量
        """
        if abs(vector_weight + keyword_weight - 1.0) > 0.01:
            raise ValueError("权重之和必须等于1.0")
        
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        
        # 向量检索器
        self.vector_retriever = vector_store.as_retriever(
            search_kwargs={"k": vector_k}
        )
        
        # 关键词检索器（BM25）
        try:
            self.keyword_retriever = BM25Retriever.from_documents(documents)
            self.keyword_retriever.k = keyword_k
        except Exception as e:
            logger.warning(f"初始化BM25检索器失败: {e}，将只使用向量检索")
            self.keyword_retriever = None
        
        # 混合检索器
        if self.keyword_retriever:
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.vector_retriever, self.keyword_retriever],
                weights=[vector_weight, keyword_weight]
            )
        else:
            self.ensemble_retriever = self.vector_retriever
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            
        Returns:
            相关文档列表
        """
        try:
            if isinstance(self.ensemble_retriever, EnsembleRetriever):
                return self.ensemble_retriever.get_relevant_documents(query)
            else:
                return self.ensemble_retriever.get_relevant_documents(query)
        except Exception as e:
            logger.error(f"混合检索失败: {e}", exc_info=True)
            # 降级到向量检索
            return self.vector_retriever.get_relevant_documents(query)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """
        异步检索相关文档
        
        Args:
            query: 查询文本
            
        Returns:
            相关文档列表
        """
        try:
            if hasattr(self.ensemble_retriever, 'aget_relevant_documents'):
                return await self.ensemble_retriever.aget_relevant_documents(query)
            else:
                return self.get_relevant_documents(query)
        except Exception as e:
            logger.error(f"异步混合检索失败: {e}", exc_info=True)
            return self.get_relevant_documents(query)


