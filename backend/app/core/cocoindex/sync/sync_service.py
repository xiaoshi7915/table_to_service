"""
同步服务
统一管理所有数据源的同步任务
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from threading import Lock

from app.core.cocoindex.sources.source_registry import source_registry
from app.core.cocoindex.pipelines.knowledge_pipeline import KnowledgePipeline
from app.core.cocoindex.pipelines.document_pipeline import DocumentPipeline
from app.core.cocoindex.pipelines.schema_pipeline import SchemaPipeline
from app.core.cocoindex.indexes.postgres_index import PostgresIndex
from app.core.cocoindex.transformers.knowledge_transformer import KnowledgeTransformer
from app.core.cocoindex.transformers.document_transformer import DocumentTransformer
from app.core.cocoindex.transformers.schema_transformer import SchemaTransformer
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService


class SyncService:
    """同步服务"""
    
    def __init__(self):
        self._sync_tasks: Dict[str, Any] = {}
        self._lock = Lock()
        self._running = False
    
    def start_sync(self, source_type: str, source_name: str) -> Dict[str, Any]:
        """
        启动同步任务
        
        Args:
            source_type: 数据源类型
            source_name: 数据源名称
            
        Returns:
            同步结果
        """
        source_key = f"{source_type}:{source_name}"
        
        with self._lock:
            if source_key in self._sync_tasks:
                return {
                    "success": False,
                    "message": "同步任务已存在"
                }
        
        try:
            source = source_registry.get_source(source_type, source_name)
            if not source:
                return {
                    "success": False,
                    "message": f"数据源不存在: {source_key}"
                }
            
            # 根据数据源类型选择管道
            pipeline = self._create_pipeline(source_type, source)
            if not pipeline:
                return {
                    "success": False,
                    "message": f"无法创建管道: {source_type}"
                }
            
            # 运行管道
            result = pipeline.run()
            
            # 更新最后同步时间
            source.update_last_sync_time(datetime.now())
            
            with self._lock:
                self._sync_tasks[source_key] = {
                    "status": "completed",
                    "last_sync": datetime.now(),
                    "result": result
                }
            
            return {
                "success": True,
                "message": "同步完成",
                "result": result
            }
        except Exception as e:
            logger.error(f"同步失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"同步失败: {str(e)}"
            }
    
    def _create_pipeline(self, source_type: str, source) -> Optional[Any]:
        """创建管道"""
        try:
            # 创建嵌入服务
            embedding_service = ChineseEmbeddingService()
            
            # 根据数据源类型创建相应的管道
            if source_type == "postgresql":
                # 知识库管道
                transformer = KnowledgeTransformer(embedding_service=embedding_service)
                index = PostgresIndex(collection_name="knowledge")
                return KnowledgePipeline(source, transformer, index)
            
            elif source_type == "file":
                # 文档管道
                transformer = DocumentTransformer(embedding_service=embedding_service)
                index = PostgresIndex(collection_name="documents")
                return DocumentPipeline(source, transformer, index)
            
            elif source_type == "database_schema":
                # Schema管道
                transformer = SchemaTransformer(embedding_service=embedding_service)
                index = PostgresIndex(collection_name="schemas")
                return SchemaPipeline(source, transformer, index)
            
            else:
                logger.warning(f"不支持的数据源类型: {source_type}")
                return None
        except Exception as e:
            logger.error(f"创建管道失败: {e}", exc_info=True)
            return None
    
    def get_sync_status(self, source_type: Optional[str] = None, source_name: Optional[str] = None) -> Dict[str, Any]:
        """获取同步状态"""
        with self._lock:
            if source_type and source_name:
                source_key = f"{source_type}:{source_name}"
                return self._sync_tasks.get(source_key, {})
            else:
                return {
                    "tasks": self._sync_tasks,
                    "total": len(self._sync_tasks)
                }
    
    def stop_all(self):
        """停止所有同步任务"""
        with self._lock:
            self._running = False
            self._sync_tasks.clear()
        logger.info("所有同步任务已停止")


# 全局同步服务实例
sync_service = SyncService()

