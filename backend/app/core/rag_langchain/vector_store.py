"""
基于pgvector的向量存储服务
使用LangChain的PGVector实现
"""
from typing import List, Optional, Dict, Any
from langchain.vectorstores import PGVector
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from loguru import logger
from app.core.config import settings


class PGVectorStore:
    """基于pgvector的向量存储"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: Embeddings,
        collection_name: str
    ):
        """
        初始化向量存储
        
        Args:
            connection_string: PostgreSQL连接字符串
            embedding_service: 嵌入服务
            collection_name: 集合名称（表名）
        """
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        
        try:
            # 创建PGVector实例
            self.vector_store = PGVector(
                connection_string=connection_string,
                embedding_function=embedding_service,
                collection_name=collection_name,
                use_jsonb=True,  # 使用JSONB存储元数据
                pre_delete_collection=False  # 不删除现有集合
            )
            logger.info(f"成功初始化向量存储: {collection_name}")
        except Exception as e:
            logger.error(f"初始化向量存储失败: {e}", exc_info=True)
            raise
    
    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: LangChain Document对象列表
            ids: 文档ID列表（可选）
            
        Returns:
            添加的文档ID列表
        """
        try:
            return self.vector_store.add_documents(
                documents=documents,
                ids=ids
            )
        except Exception as e:
            logger.error(f"添加文档失败: {e}", exc_info=True)
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回数量
            filter: 过滤条件（元数据过滤）
            
        Returns:
            相关文档列表
        """
        try:
            return self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}", exc_info=True)
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[tuple]:
        """
        相似度搜索（带分数）
        
        Args:
            query: 查询文本
            k: 返回数量
            filter: 过滤条件
            
        Returns:
            (Document, score)元组列表
        """
        try:
            return self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
        except Exception as e:
            logger.error(f"相似度搜索（带分数）失败: {e}", exc_info=True)
            return []
    
    def as_retriever(self, **kwargs):
        """
        转换为检索器
        
        Args:
            **kwargs: 检索器参数
            
        Returns:
            LangChain检索器对象
        """
        return self.vector_store.as_retriever(**kwargs)
    
    def delete(self, ids: Optional[List[str]] = None):
        """
        删除文档
        
        Args:
            ids: 要删除的文档ID列表（如果为None，删除所有）
        """
        try:
            if ids:
                self.vector_store.delete(ids=ids)
            else:
                # 删除整个集合
                self.vector_store.delete_collection()
            logger.info(f"删除文档成功: {ids or 'all'}")
        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
            raise


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: Embeddings
    ):
        """
        初始化管理器
        
        Args:
            connection_string: PostgreSQL连接字符串
            embedding_service: 嵌入服务
        """
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        
        # 创建各个集合的向量存储
        self.stores = {
            "terminologies": PGVectorStore(
                connection_string=connection_string,
                embedding_service=embedding_service,
                collection_name="terminologies"
            ),
            "sql_examples": PGVectorStore(
                connection_string=connection_string,
                embedding_service=embedding_service,
                collection_name="sql_examples"
            ),
            "knowledge": PGVectorStore(
                connection_string=connection_string,
                embedding_service=embedding_service,
                collection_name="knowledge"
            )
        }
    
    def get_store(self, store_type: str) -> PGVectorStore:
        """
        获取指定类型的向量存储
        
        Args:
            store_type: 存储类型（terminologies/sql_examples/knowledge）
            
        Returns:
            向量存储对象
        """
        if store_type not in self.stores:
            raise ValueError(f"未知的存储类型: {store_type}")
        return self.stores[store_type]


