"""
CocoIndex 检索器适配器
将 CocoIndex 检索器适配为 LangChain BaseRetriever 接口
"""
from typing import List
from loguru import logger

try:
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import BaseRetriever, Document

from app.core.cocoindex.retrievers.hybrid_strategy import HybridRetrievalStrategy
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService
from app.core.database import get_local_db


class CocoIndexRetrieverAdapter(BaseRetriever):
    """CocoIndex 检索器适配器（兼容 LangChain BaseRetriever）"""
    
    def __init__(
        self,
        collection_name: str,
        embedding_service: ChineseEmbeddingService = None,
        db_session = None
    ):
        """
        初始化适配器
        
        Args:
            collection_name: 集合名称
            embedding_service: 嵌入服务
            db_session: 数据库会话
        """
        super().__init__()
        self.collection_name = collection_name
        self.hybrid_strategy = HybridRetrievalStrategy(
            collection_name=collection_name,
            embedding_service=embedding_service,
            db_session=db_session
        )
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        检索相关文档（LangChain接口）
        
        Args:
            query: 查询文本
            
        Returns:
            Document 列表
        """
        try:
            # 使用混合召回策略检索
            results = self.hybrid_strategy.retrieve(query, limit=10)
            
            # 转换为 LangChain Document
            documents = []
            for result in results:
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                
                # 添加相似度分数
                if "score" in result:
                    metadata["score"] = result["score"]
                
                documents.append(Document(
                    page_content=content,
                    metadata=metadata
                ))
            
            return documents
        except Exception as e:
            logger.error(f"CocoIndex检索失败: {e}", exc_info=True)
            return []
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """异步检索（LangChain接口）"""
        # 当前实现为同步，直接调用同步方法
        return self._get_relevant_documents(query)

