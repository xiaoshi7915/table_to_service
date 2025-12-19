"""
混合检索器
结合向量检索和关键词检索（BM25）
"""
from typing import List, Dict, Any, Optional, Protocol
try:
    # LangChain 1.x
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document
    try:
        from langchain_core.vectorstores import VectorStore
    except ImportError:
        try:
            from langchain.vectorstores import VectorStore
        except ImportError:
            # 如果 VectorStore 不可用，定义一个 Protocol
            class VectorStore(Protocol):
                def as_retriever(self, **kwargs):
                    ...
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.retrievers import BM25Retriever
    from langchain.schema import Document
    try:
        from langchain.vectorstores import VectorStore
    except ImportError:
        class VectorStore(Protocol):
            def as_retriever(self, **kwargs):
                ...

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
        
        # 标记是否使用混合检索
        self.use_ensemble = self.keyword_retriever is not None
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            
        Returns:
            相关文档列表
        """
        try:
            if self.use_ensemble and self.keyword_retriever:
                # 手动实现混合检索
                vector_docs = self.vector_retriever.get_relevant_documents(query)
                keyword_docs = self.keyword_retriever.get_relevant_documents(query)
                
                # 合并结果（去重，按权重排序）
                doc_dict = {}
                for doc in vector_docs:
                    doc_id = doc.page_content[:50]  # 使用内容前50字符作为ID
                    doc_dict[doc_id] = (doc, self.vector_weight)
                
                for doc in keyword_docs:
                    doc_id = doc.page_content[:50]
                    if doc_id in doc_dict:
                        # 如果已存在，增加权重
                        _, weight = doc_dict[doc_id]
                        doc_dict[doc_id] = (doc, weight + self.keyword_weight)
                    else:
                        doc_dict[doc_id] = (doc, self.keyword_weight)
                
                # 按权重排序并返回文档
                sorted_docs = sorted(doc_dict.values(), key=lambda x: x[1], reverse=True)
                return [doc for doc, _ in sorted_docs]
            else:
                return self.vector_retriever.get_relevant_documents(query)
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
            if self.use_ensemble and self.keyword_retriever:
                # 异步执行混合检索
                import asyncio
                vector_task = asyncio.create_task(
                    self._async_get_docs(self.vector_retriever, query)
                )
                keyword_task = asyncio.create_task(
                    self._async_get_docs(self.keyword_retriever, query)
                )
                vector_docs, keyword_docs = await asyncio.gather(vector_task, keyword_task)
                
                # 合并结果（与同步版本相同）
                doc_dict = {}
                for doc in vector_docs:
                    doc_id = doc.page_content[:50]
                    doc_dict[doc_id] = (doc, self.vector_weight)
                
                for doc in keyword_docs:
                    doc_id = doc.page_content[:50]
                    if doc_id in doc_dict:
                        _, weight = doc_dict[doc_id]
                        doc_dict[doc_id] = (doc, weight + self.keyword_weight)
                    else:
                        doc_dict[doc_id] = (doc, self.keyword_weight)
                
                sorted_docs = sorted(doc_dict.values(), key=lambda x: x[1], reverse=True)
                return [doc for doc, _ in sorted_docs]
            else:
                if hasattr(self.vector_retriever, 'aget_relevant_documents'):
                    return await self.vector_retriever.aget_relevant_documents(query)
                else:
                    return self.get_relevant_documents(query)
        except Exception as e:
            logger.error(f"异步混合检索失败: {e}", exc_info=True)
            return self.get_relevant_documents(query)
    
    async def _async_get_docs(self, retriever, query: str) -> List[Document]:
        """辅助方法：异步获取文档"""
        if hasattr(retriever, 'aget_relevant_documents'):
            return await retriever.aget_relevant_documents(query)
        else:
            return retriever.get_relevant_documents(query)
