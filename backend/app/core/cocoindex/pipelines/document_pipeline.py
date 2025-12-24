"""
文档索引管道
将文档上传、解析、分块后索引到向量数据库
"""
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    import cocoindex
    from cocoindex.targets import Postgres
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False

from app.core.cocoindex.sources.file_source import FileSource
from app.core.cocoindex.transformers.document_transformer import DocumentTransformer
from app.core.cocoindex.indexes.postgres_index import PostgresIndex
from app.core.cocoindex.parsers.parser_factory import ParserFactory
from app.core.cocoindex.chunkers.document_chunker import DocumentChunker
from app.core.cocoindex.extractors.metadata_extractor import MetadataExtractor


class DocumentPipeline:
    """文档索引管道"""
    
    def __init__(
        self,
        source: FileSource,
        transformer: DocumentTransformer,
        index: PostgresIndex
    ):
        """
        初始化管道
        
        Args:
            source: 文件数据源
            transformer: 文档转换器
            index: 索引
        """
        self.source = source
        self.transformer = transformer
        self.index = index
        self.chunker = DocumentChunker()
        self.extractor = MetadataExtractor()
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理结果
        """
        try:
            # 1. 解析文档
            parser = ParserFactory.create_parser(file_path)
            document_data = parser.parse()
            metadata = parser.extract_metadata()
            
            # 2. 提取元数据
            extracted_metadata = self.extractor.extract(document_data, file_path)
            metadata.update(extracted_metadata)
            
            # 3. 分块文档
            chunks = self.chunker.chunk_document(document_data, metadata)
            
            # 4. 转换为 Document 格式
            transform_data = {
                "chunks": chunks,
                "metadata": metadata,
                "document_id": None,  # 如果需要关联文档ID
            }
            
            documents = self.transformer.transform(transform_data)
            
            # 5. 索引数据
            indexed_count = 0
            if COCOINDEX_AVAILABLE:
                try:
                    indexed_count = self._index_with_cocoindex(documents)
                except Exception as e:
                    logger.warning(f"CocoIndex 索引失败，使用直接数据库插入: {e}")
                    indexed_count = self._index_directly(documents)
            else:
                indexed_count = self._index_directly(documents)
            
            return {
                "success": True,
                "chunks_count": len(chunks),
                "documents_count": len(documents),
                "indexed_count": indexed_count,
            }
        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_count": 0,
                "documents_count": 0,
                "indexed_count": 0,
            }
    
    def _index_with_cocoindex(self, documents: List[Dict[str, Any]]) -> int:
        """使用 CocoIndex 索引数据"""
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
        """直接插入数据库（降级方案，使用批量插入优化性能）"""
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
    
    def run(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        运行管道：扫描文件 → 处理 → 索引
        
        Args:
            limit: 限制处理数量
            
        Returns:
            处理结果统计
        """
        try:
            # 1. 从文件源读取文件列表
            files = self.source.read(limit=limit)
            logger.info(f"找到 {len(files)} 个文件")
            
            # 2. 处理每个文件
            processed_count = 0
            failed_count = 0
            
            for file_info in files:
                file_path = file_info["file_path"]
                try:
                    result = self.process_file(file_path)
                    if result["success"]:
                        processed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"处理文件失败 {file_path}: {e}")
                    failed_count += 1
            
            return {
                "success": True,
                "files_found": len(files),
                "processed": processed_count,
                "failed": failed_count,
            }
        except Exception as e:
            logger.error(f"管道执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

