"""
CocoIndex 检索器
封装 CocoIndex 的检索接口
"""
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    import cocoindex
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False

from app.core.cocoindex.config import cocoindex_config


class CocoIndexRetriever:
    """CocoIndex 检索器"""
    
    def __init__(self, collection_name: str):
        """
        初始化检索器
        
        Args:
            collection_name: 集合名称
        """
        self.collection_name = collection_name
        self.use_cocoindex = COCOINDEX_AVAILABLE
        
        if not COCOINDEX_AVAILABLE:
            logger.warning("cocoindex 未安装，将使用直接数据库查询")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 查询文本
            limit: 返回数量
            filters: 过滤条件（元数据过滤）
            
        Returns:
            搜索结果列表
        """
        # 如果 CocoIndex 可用，尝试使用 CocoIndex API
        if COCOINDEX_AVAILABLE:
            try:
                return self._search_with_cocoindex(query, limit, filters)
            except Exception as e:
                logger.warning(f"CocoIndex 检索失败，使用直接数据库查询: {e}")
                return self._search_directly(query, limit, filters)
        else:
            return self._search_directly(query, limit, filters)
    
    def _search_with_cocoindex(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """使用 CocoIndex API 检索"""
        try:
            from app.core.cocoindex.utils.cocoindex_adapter import CocoIndexAdapter
            from app.core.cocoindex.config import cocoindex_config
            
            # 使用适配器进行搜索
            adapter = CocoIndexAdapter(
                collection_name=self.collection_name,
                connection_string=cocoindex_config.POSTGRESQL_CONNECTION_STRING
            )
            
            return adapter.search(query, limit, filters)
        except Exception as e:
            logger.warning(f"适配器搜索失败: {e}")
            return self._search_directly(query, limit, filters)
    
    def _search_directly(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """直接数据库查询（降级方案）"""
        try:
            from app.core.database import LocalSessionLocal
            from sqlalchemy import text
            
            db = LocalSessionLocal()
            try:
                # 构建查询，包含相似度分数计算
                if query:
                    # 使用全文检索，计算 ts_rank 分数
                    sql = """
                    SELECT 
                        id,
                        content,
                        meta_data,
                        embedding,
                        ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) as rank_score
                    FROM document_chunks
                    WHERE 1=1
                    """
                    params = {"query": query}
                else:
                    # 没有查询文本时，只返回记录
                    sql = """
                    SELECT 
                        id,
                        content,
                        meta_data,
                        embedding,
                        1.0 as rank_score
                    FROM document_chunks
                    WHERE 1=1
                    """
                    params = {}
                
                # 添加集合过滤
                sql += " AND meta_data->>'source_type' = :collection"
                params["collection"] = self.collection_name
                
                # 添加全文检索条件
                if query:
                    sql += " AND to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)"
                
                # 添加元数据过滤
                if filters:
                    for key, value in filters.items():
                        sql += f" AND meta_data->>'{key}' = :filter_{key}"
                        params[f"filter_{key}"] = str(value)
                
                # 添加排序和限制
                sql += " ORDER BY rank_score DESC"
                sql += " LIMIT :limit"
                params["limit"] = limit
                
                result = db.execute(text(sql), params)
                rows = result.fetchall()
                
                # 返回结果，包含实际计算的相似度分数
                return [
                    {
                        "id": row[0],
                        "content": row[1],
                        "metadata": row[2] if isinstance(row[2], dict) else {},
                        "embedding": row[3],
                        "score": float(row[4]) if row[4] is not None else 0.0
                    }
                    for row in rows
                ]
            finally:
                db.close()
        except Exception as e:
            logger.error(f"直接数据库查询失败: {e}", exc_info=True)
            return []
    
    def search_by_vector(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            query_vector: 查询向量
            limit: 返回数量
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        # 如果 CocoIndex 可用，尝试使用 CocoIndex API
        if COCOINDEX_AVAILABLE:
            try:
                return self._search_vector_with_cocoindex(query_vector, limit, filters)
            except Exception as e:
                logger.warning(f"CocoIndex 向量搜索失败，使用直接数据库查询: {e}")
                return self._search_vector_directly(query_vector, limit, filters)
        else:
            return self._search_vector_directly(query_vector, limit, filters)
    
    def _search_vector_with_cocoindex(
        self,
        query_vector: List[float],
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """使用 CocoIndex API 向量搜索"""
        # 向量搜索目前使用直接数据库查询（pgvector）
        # 如果 CocoIndex 提供向量搜索 API，可以在这里实现
        logger.debug("CocoIndex API 向量搜索使用直接数据库查询")
        return self._search_vector_directly(query_vector, limit, filters)
    
    def _search_vector_directly(
        self,
        query_vector: List[float],
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """直接数据库向量查询（降级方案）"""
        try:
            from app.core.database import LocalSessionLocal
            from sqlalchemy import text
            
            db = LocalSessionLocal()
            try:
                # 构建向量查询
                sql = """
                SELECT 
                    id,
                    content,
                    meta_data,
                    embedding,
                    1 - (embedding <=> :query_vector::vector) as similarity
                FROM document_chunks
                WHERE embedding IS NOT NULL
                """
                params = {"query_vector": str(query_vector)}
                
                # 添加元数据过滤
                if filters:
                    for key, value in filters.items():
                        sql += f" AND meta_data->>'{key}' = :filter_{key}"
                        params[f"filter_{key}"] = str(value)
                
                # 添加集合过滤（如果指定）
                if self.collection_name:
                    sql += " AND meta_data->>'source_type' = :collection"
                    params["collection"] = self.collection_name
                
                # 排序和限制
                sql += " ORDER BY embedding <=> :query_vector::vector LIMIT :limit"
                params["limit"] = limit
                
                result = db.execute(text(sql), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": row[0],
                        "content": row[1],
                        "metadata": row[2] if isinstance(row[2], dict) else {},
                        "embedding": row[3],
                        "score": float(row[4]) if row[4] is not None else 0.0
                    }
                    for row in rows
                ]
            finally:
                db.close()
        except Exception as e:
            logger.error(f"直接向量查询失败: {e}", exc_info=True)
            return []

