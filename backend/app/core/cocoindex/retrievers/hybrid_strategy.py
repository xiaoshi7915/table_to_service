"""
混合召回策略
结合向量检索、关键词检索和元数据过滤
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.cocoindex.retrievers.cocoindex_retriever import CocoIndexRetriever
from app.core.cocoindex.config import cocoindex_config
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService


class HybridRetrievalStrategy:
    """混合召回策略"""
    
    def __init__(
        self,
        collection_name: str,
        embedding_service: Optional[ChineseEmbeddingService] = None,
        db_session: Optional[Session] = None
    ):
        """
        初始化混合召回策略
        
        Args:
            collection_name: 集合名称
            embedding_service: 嵌入服务（用于生成查询向量）
            db_session: 数据库会话（用于全文检索）
        """
        self.collection_name = collection_name
        self.retriever = CocoIndexRetriever(collection_name)
        self.embedding_service = embedding_service
        self.db_session = db_session
    
    def retrieve(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        混合检索
        
        Args:
            query: 查询文本
            limit: 返回数量
            filters: 元数据过滤条件
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
            
        Returns:
            融合后的搜索结果
        """
        results = []
        
        # 1. 向量检索
        vector_results = []
        if self.embedding_service and vector_weight > 0:
            try:
                query_vector = self.embedding_service.generate_embedding(query)
                vector_results = self.retriever.search_by_vector(
                    query_vector=query_vector,
                    limit=int(limit * 2),  # 获取更多结果用于融合
                    filters=filters
                )
                logger.debug(f"向量检索返回 {len(vector_results)} 条结果")
            except Exception as e:
                logger.warning(f"向量检索失败: {e}")
        
        # 2. 关键词检索（全文检索）
        keyword_results = []
        if self.db_session and keyword_weight > 0:
            try:
                keyword_results = self._fulltext_search(query, limit=int(limit * 2), filters=filters)
                logger.debug(f"关键词检索返回 {len(keyword_results)} 条结果")
            except Exception as e:
                logger.warning(f"关键词检索失败: {e}")
        
        # 3. 结果融合（RRF - Reciprocal Rank Fusion）
        fused_results = self._rrf_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            limit=limit,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight
        )
        
        return fused_results
    
    def _fulltext_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        全文检索（使用 PostgreSQL tsvector）
        
        Args:
            query: 查询文本
            limit: 返回数量
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self.db_session:
            return []
        
        try:
            # 构建 SQL 查询
            # 这里需要根据实际的表结构调整
            sql = """
            SELECT 
                id,
                content,
                metadata,
                ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) as rank
            FROM document_chunks
            WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
            """
            
            # 添加元数据过滤
            if filters:
                for key, value in filters.items():
                    sql += f" AND metadata->>'{key}' = :{key}"
            
            sql += " ORDER BY rank DESC LIMIT :limit"
            
            # 执行查询
            params = {"query": query, "limit": limit}
            if filters:
                params.update(filters)
            
            result = self.db_session.execute(text(sql), params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2] if isinstance(row[2], dict) else {},
                    "score": float(row[3]),
                    "source": "keyword"
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"全文检索失败: {e}")
            return []
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        结果融合（RRF - Reciprocal Rank Fusion）
        
        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            limit: 返回数量
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
            
        Returns:
            融合后的结果列表
        """
        # 计算 RRF 分数
        rrf_scores = {}
        k = 60  # RRF 常数（通常使用 60）
        
        # 处理向量检索结果
        for rank, result in enumerate(vector_results, 1):
            doc_id = result.get("id") or str(result.get("content", ""))[:100]
            rrf_score = vector_weight / (k + rank)
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {
                    "result": result,
                    "score": 0.0
                }
            rrf_scores[doc_id]["score"] += rrf_score
        
        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results, 1):
            doc_id = result.get("id") or str(result.get("content", ""))[:100]
            rrf_score = keyword_weight / (k + rank)
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {
                    "result": result,
                    "score": 0.0
                }
            rrf_scores[doc_id]["score"] += rrf_score
        
        # 按分数排序
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        # 返回前 limit 个结果
        return [item["result"] for item in sorted_results[:limit]]

