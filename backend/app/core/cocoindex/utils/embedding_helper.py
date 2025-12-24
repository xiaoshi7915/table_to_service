"""
向量嵌入辅助工具
统一管理向量生成和存储
"""
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.rag_langchain.embedding_service import ChineseEmbeddingService
from app.core.cocoindex.config import cocoindex_config


class EmbeddingHelper:
    """向量嵌入辅助工具"""
    
    def __init__(self, embedding_service: Optional[Any] = None):
        """
        初始化辅助工具
        
        Args:
            embedding_service: 嵌入服务
        """
        if embedding_service:
            self.embedding_service = embedding_service
        elif EMBEDDING_SERVICE_AVAILABLE:
            self.embedding_service = ChineseEmbeddingService()
        else:
            self.embedding_service = None
            logger.warning("嵌入服务不可用，向量生成功能将受限")
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        批量生成向量
        
        Args:
            texts: 文本列表
            batch_size: 批次大小
            
        Returns:
            向量列表（可能包含 None）
        """
        if not self.embedding_service:
            logger.warning("嵌入服务不可用，无法生成向量")
            return [None] * len(texts)
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_embeddings = [
                    self.embedding_service.generate_embedding(text)
                    for text in batch
                ]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"批量生成向量失败: {e}")
                # 为失败的批次添加 None
                embeddings.extend([None] * len(batch))
        
        return embeddings
    
    def update_document_chunk_embeddings(
        self,
        db: Session,
        document_id: Optional[int] = None,
        chunk_ids: Optional[List[int]] = None
    ) -> int:
        """
        更新文档分块的向量
        
        Args:
            db: 数据库会话
            document_id: 文档ID（可选）
            chunk_ids: 分块ID列表（可选）
            
        Returns:
            更新的分块数量
        """
        try:
            from app.models import DocumentChunk
            
            # 构建查询
            query = db.query(DocumentChunk).filter(DocumentChunk.embedding.is_(None))
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            if chunk_ids:
                query = query.filter(DocumentChunk.id.in_(chunk_ids))
            
            chunks = query.all()
            
            if not chunks:
                return 0
            
            # 批量生成向量
            texts = [chunk.content for chunk in chunks]
            embeddings = self.generate_embeddings_batch(texts)
            
            # 更新数据库
            updated_count = 0
            for chunk, embedding in zip(chunks, embeddings):
                if embedding:
                    chunk.embedding = embedding
                    updated_count += 1
            
            db.commit()
            logger.info(f"更新了 {updated_count} 个分块的向量")
            return updated_count
        except Exception as e:
            db.rollback()
            logger.error(f"更新向量失败: {e}", exc_info=True)
            return 0
    
    def ensure_all_embeddings(self, db: Session) -> Dict[str, int]:
        """
        确保所有文档分块都有向量
        
        Args:
            db: 数据库会话
            
        Returns:
            统计信息
        """
        try:
            from app.models import DocumentChunk
            
            # 统计需要更新的分块
            total_chunks = db.query(DocumentChunk).count()
            chunks_without_embedding = db.query(DocumentChunk).filter(
                DocumentChunk.embedding.is_(None)
            ).count()
            
            if chunks_without_embedding == 0:
                return {
                    "total": total_chunks,
                    "updated": 0,
                    "already_have": total_chunks
                }
            
            # 批量更新
            updated = self.update_document_chunk_embeddings(db)
            
            return {
                "total": total_chunks,
                "updated": updated,
                "already_have": total_chunks - chunks_without_embedding,
                "remaining": chunks_without_embedding - updated
            }
        except Exception as e:
            logger.error(f"确保向量失败: {e}", exc_info=True)
            return {"error": str(e)}

