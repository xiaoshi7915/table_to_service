"""
CocoIndex 适配器
提供统一的接口，支持 CocoIndex 库和直接数据库操作
"""
from typing import List, Dict, Any, Optional, Iterator
from loguru import logger

try:
    import cocoindex
    from cocoindex.targets import Postgres
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False
    logger.warning("cocoindex 未安装，将使用直接数据库操作")


class CocoIndexAdapter:
    """CocoIndex 适配器"""
    
    def __init__(
        self,
        collection_name: str,
        connection_string: Optional[str] = None
    ):
        """
        初始化适配器
        
        Args:
            collection_name: 集合名称
            connection_string: PostgreSQL 连接字符串
        """
        self.collection_name = collection_name
        self.connection_string = connection_string
        
        if COCOINDEX_AVAILABLE:
            try:
                # 解析连接字符串获取数据库配置
                from app.core.cocoindex.utils.connection_parser import parse_connection_string
                db_spec = parse_connection_string(connection_string) if connection_string else None
                
                # 初始化 CocoIndex Postgres Target
                # 注意：Postgres Target 使用 table_name 和 database 参数
                self.target = Postgres(
                    table_name=collection_name,
                    database=db_spec
                )
                self.use_cocoindex = True
                logger.info(f"CocoIndex 适配器已初始化: {collection_name}")
            except Exception as e:
                logger.warning(f"CocoIndex 初始化失败，将使用直接数据库操作: {e}")
                self.use_cocoindex = False
                self.target = None
        else:
            self.use_cocoindex = False
            self.target = None
    
    def export(
        self,
        documents: Iterator[Dict[str, Any]],
        primary_key_fields: Optional[List[str]] = None,
        vector_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        导出数据到索引
        
        Args:
            documents: 文档迭代器
            primary_key_fields: 主键字段列表
            vector_fields: 向量字段列表
            
        Returns:
            导出结果统计
        """
        if self.use_cocoindex and COCOINDEX_AVAILABLE:
            try:
                return self._export_with_cocoindex(documents, primary_key_fields, vector_fields)
            except Exception as e:
                logger.warning(f"CocoIndex 导出失败，降级到直接数据库操作: {e}")
                return self._export_directly(documents)
        else:
            return self._export_directly(documents)
    
    def _export_with_cocoindex(
        self,
        documents: Iterator[Dict[str, Any]],
        primary_key_fields: Optional[List[str]],
        vector_fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        """使用 CocoIndex Flow 导出"""
        try:
            # 注意：CocoIndex Flow 模式适用于从数据库表同步到另一个表
            # 我们的场景是数据在内存中，需要直接插入
            # 因此使用直接数据库操作更合适
            # 如果需要使用 CocoIndex Flow，需要先将数据插入到源表
            
            logger.debug("CocoIndex Flow 模式需要数据在数据库表中")
            logger.debug("当前数据在内存中，使用直接数据库操作")
            return self._export_directly(documents)
        except Exception as e:
            logger.error(f"CocoIndex 导出失败: {e}")
            # 降级到直接数据库操作
            return self._export_directly(documents)
    
    def _export_directly(self, documents: Iterator[Dict[str, Any]]) -> Dict[str, Any]:
        """直接数据库操作（降级方案）"""
        try:
            from app.core.database import LocalSessionLocal
            from app.models import DocumentChunk
            from app.core.cocoindex.utils.batch_processor import BatchProcessor
            
            db = LocalSessionLocal()
            try:
                # 转换为列表（如果已经是列表则直接使用）
                if isinstance(documents, list):
                    doc_list = documents
                else:
                    doc_list = list(documents)
                
                # 使用批量处理器
                batch_processor = BatchProcessor(batch_size=100)
                
                def process_batch(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
                    """处理一批文档"""
                    try:
                        chunks = []
                        for doc in batch:
                            content = doc.get("content", "")
                            metadata = doc.get("metadata", {})
                            embedding = doc.get("embedding")
                            
                            chunk = DocumentChunk(
                                document_id=metadata.get("document_id"),
                                chunk_index=metadata.get("chunk_index", 0),
                                content=content,
                                meta_data=metadata,
                                embedding=embedding
                            )
                            chunks.append(chunk)
                        
                        # 批量插入
                        db.bulk_save_objects(chunks)
                        db.commit()
                        
                        return {
                            "success": True,
                            "processed": len(batch)
                        }
                    except Exception as e:
                        db.rollback()
                        logger.error(f"批量插入失败: {e}")
                        return {
                            "success": False,
                            "error": str(e)
                        }
                
                # 批量处理
                result = batch_processor.process(doc_list, process_batch)
                
                return {
                    "success": True,
                    "count": result.get("success", 0),
                    "method": "direct_database"
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"直接数据库导出失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "count": 0
            }
    
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
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if self.use_cocoindex and COCOINDEX_AVAILABLE:
            try:
                return self._search_with_cocoindex(query, limit, filters)
            except Exception as e:
                logger.warning(f"CocoIndex 搜索失败，降级到直接数据库查询: {e}")
                return self._search_directly(query, limit, filters)
        else:
            return self._search_directly(query, limit, filters)
    
    def _search_with_cocoindex(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """使用 CocoIndex Flow 查询处理器搜索"""
        try:
            from app.core.cocoindex.utils.cocoindex_flow_manager import flow_manager
            from app.core.cocoindex.config import cocoindex_config
            
            # 尝试使用 Flow 的查询处理器
            # 注意：CocoIndex Flow 的查询需要通过 query_handler
            # 如果 Flow 已配置查询处理器，可以使用它
            
            flow_name = f"flow_{self.collection_name}"
            try:
                flow = flow_manager.get_flow(flow_name)
                
                # 尝试使用 Flow 的查询处理器
                # 注意：这需要 Flow 中已配置 query_handler
                # 如果没有配置，降级到直接数据库查询
                logger.debug(f"尝试使用 Flow {flow_name} 的查询处理器")
                
                # 由于 CocoIndex Flow 的查询处理器需要预先配置
                # 这里先使用直接数据库查询，但保留 Flow 查询的接口
                # 实际使用时，可以通过 Flow 的 add_query_handler 配置查询逻辑
                return self._search_directly(query, limit, filters)
                
            except ValueError:
                # Flow 不存在，使用直接数据库查询
                logger.debug(f"Flow {flow_name} 不存在，使用直接数据库查询")
                return self._search_directly(query, limit, filters)
        except Exception as e:
            logger.warning(f"CocoIndex Flow 查询失败: {e}")
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
                # 构建查询
                sql = """
                SELECT 
                    id,
                    content,
                    metadata,
                    embedding
                FROM document_chunks
                WHERE 1=1
                """
                params = {}
                
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

