"""
数据库 Schema 索引管道
将数据库表结构索引到向量数据库
"""
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.cocoindex.sources.database_schema_source import DatabaseSchemaSource
from app.core.cocoindex.transformers.schema_transformer import SchemaTransformer
from app.core.cocoindex.indexes.postgres_index import PostgresIndex


class SchemaPipeline:
    """数据库 Schema 索引管道"""
    
    def __init__(
        self,
        source: DatabaseSchemaSource,
        transformer: SchemaTransformer,
        index: PostgresIndex
    ):
        """
        初始化管道
        
        Args:
            source: Schema 数据源
            transformer: Schema 转换器
            index: 索引
        """
        self.source = source
        self.transformer = transformer
        self.index = index
    
    def run(
        self,
        limit: Optional[int] = None,
        table_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行管道：读取 Schema → 转换 → 索引
        
        Args:
            limit: 限制处理数量
            table_names: 可选，指定要处理的表名列表
            
        Returns:
            处理结果统计
        """
        try:
            # 1. 从数据源读取 Schema
            logger.info(f"开始读取数据库 Schema: {self.source.name}")
            schema_data = self.source.read(limit=limit, table_names=table_names)
            logger.info(f"读取到 {len(schema_data)} 个表的结构")
            
            # 2. 转换数据
            logger.info("开始转换 Schema 数据")
            documents = []
            for schema in schema_data:
                try:
                    transformed = self.transformer.transform(schema)
                    documents.extend(transformed)
                except Exception as e:
                    logger.warning(f"转换 Schema 失败: {e}")
                    continue
            
            logger.info(f"转换完成，生成 {len(documents)} 个文档")
            
            # 3. 索引数据
            indexed_count = 0
            try:
                indexed_count = self._index_directly(documents)
            except Exception as e:
                logger.error(f"索引失败: {e}", exc_info=True)
            
            return {
                "success": True,
                "tables_read": len(schema_data),
                "documents_created": len(documents),
                "indexed_count": indexed_count,
                "indexed": indexed_count > 0,
            }
        except Exception as e:
            logger.error(f"Schema 管道执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tables_read": 0,
                "documents_created": 0,
                "indexed_count": 0,
                "indexed": False,
            }
    
    def _index_directly(self, documents: List[Dict[str, Any]]) -> int:
        """直接插入数据库（使用批量插入优化性能）"""
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
                                document_id=None,  # Schema 数据没有关联文档
                                chunk_index=0,
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
                
                logger.info(f"直接插入 {result['success']} 个Schema文档")
                return result['success']
            finally:
                db.close()
        except Exception as e:
            logger.error(f"直接插入失败: {e}", exc_info=True)
            return 0

