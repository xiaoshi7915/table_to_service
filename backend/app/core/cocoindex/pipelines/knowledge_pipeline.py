"""
知识库索引管道
将术语库、SQL示例、自定义提示词索引到向量数据库
"""
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    import cocoindex
    from cocoindex.targets import Postgres
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False

from app.core.cocoindex.config import cocoindex_config
from app.core.cocoindex.sources.postgresql_source import PostgreSQLSource
from app.core.cocoindex.transformers.knowledge_transformer import KnowledgeTransformer
from app.core.cocoindex.indexes.postgres_index import PostgresIndex


class KnowledgePipeline:
    """知识库索引管道"""
    
    def __init__(
        self,
        source: PostgreSQLSource,
        transformer: KnowledgeTransformer,
        index: PostgresIndex
    ):
        """
        初始化管道
        
        Args:
            source: 数据源
            transformer: 数据转换器
            index: 索引
        """
        self.source = source
        self.transformer = transformer
        self.index = index
    
    def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        运行管道：读取数据 → 转换 → 索引
        
        Args:
            limit: 限制处理数量
            
        Returns:
            处理结果统计
        """
        try:
            # 1. 从数据源读取数据
            logger.info(f"开始读取数据源: {self.source.name}")
            raw_data = self.source.read(limit=limit)
            logger.info(f"读取到 {len(raw_data)} 条记录")
            
            # 2. 转换数据
            logger.info("开始转换数据")
            documents = []
            for data in raw_data:
                try:
                    transformed = self.transformer.transform(data)
                    documents.extend(transformed)
                except Exception as e:
                    logger.warning(f"转换数据失败: {e}")
                    continue
            
            logger.info(f"转换完成，生成 {len(documents)} 个文档")
            
            # 3. 索引数据
            logger.info(f"开始索引数据到: {self.index.collection_name}")
            
            # 如果 CocoIndex 可用，尝试使用 CocoIndex 索引
            indexed_count = 0
            if COCOINDEX_AVAILABLE:
                try:
                    # 尝试使用 CocoIndex export（如果API可用）
                    indexed_count = self._index_with_cocoindex(documents)
                except Exception as e:
                    logger.warning(f"CocoIndex 索引失败，使用直接数据库插入: {e}")
                    # 降级到直接数据库插入
                    indexed_count = self._index_directly(documents)
            else:
                # 如果 CocoIndex 不可用，使用直接数据库操作
                logger.warning("cocoindex 未安装，使用直接数据库操作")
                indexed_count = self._index_directly(documents)
            
            return {
                "success": True,
                "records_read": len(raw_data),
                "documents_created": len(documents),
                "indexed_count": indexed_count,
                "indexed": indexed_count > 0,
            }
        except Exception as e:
            logger.error(f"管道执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
    
    def _index_with_cocoindex(self, documents: List[Dict[str, Any]]) -> int:
        """
        使用 CocoIndex 索引数据
        
        Args:
            documents: 文档列表
            
        Returns:
            索引的文档数量
        """
        try:
            from app.core.cocoindex.utils.cocoindex_adapter import CocoIndexAdapter
            
            # 使用适配器进行导出
            adapter = CocoIndexAdapter(
                collection_name=self.index.collection_name,
                connection_string=self.index.connection_string
            )
            
            result = adapter.export(
                documents=iter(documents),
                primary_key_fields=["id"],
                vector_fields=["embedding"]
            )
            
            if result.get("success"):
                return result.get("count", 0)
            else:
                # 如果适配器导出失败，降级到直接插入
                logger.warning(f"适配器导出失败: {result.get('error')}")
                return self._index_directly(documents)
        except Exception as e:
            logger.error(f"CocoIndex 索引失败: {e}")
            # 降级到直接插入
            return self._index_directly(documents)
    
    def _index_directly(self, documents: List[Dict[str, Any]]) -> int:
        """
        直接插入数据库（降级方案，使用批量插入优化性能）
        
        Args:
            documents: 文档列表
            
        Returns:
            插入的文档数量
        """
        try:
            from app.core.database import LocalSessionLocal
            from app.models import DocumentChunk
            from app.core.cocoindex.utils.batch_processor import BatchProcessor
            
            db = LocalSessionLocal()
            try:
                # 使用批量处理器优化性能
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
                result = batch_processor.process(documents, process_batch)
                
                logger.info(f"直接插入 {result['success']} 个文档分块")
                return result['success']
            finally:
                db.close()
        except Exception as e:
            logger.error(f"直接插入失败: {e}", exc_info=True)
            return 0

