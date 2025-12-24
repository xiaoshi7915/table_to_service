"""
文档处理队列
异步处理文档上传、解析、分块、向量化
"""
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session

from app.core.cocoindex.parsers.parser_factory import ParserFactory
from app.core.cocoindex.chunkers.document_chunker import DocumentChunker
from app.core.cocoindex.extractors.metadata_extractor import MetadataExtractor
from app.core.cocoindex.config import cocoindex_config
from app.models import Document, DocumentChunk
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, db: Session, embedding_service: Optional[ChineseEmbeddingService] = None):
        """
        初始化文档处理器
        
        Args:
            db: 数据库会话
            embedding_service: 嵌入服务（用于生成向量）
        """
        self.db = db
        self.embedding_service = embedding_service
        self.chunker = DocumentChunker()
        self.extractor = MetadataExtractor()
    
    def process_document(self, document_id: int) -> Dict[str, Any]:
        """
        处理文档：解析、分块、向量化、索引
        
        Args:
            document_id: 文档ID
            
        Returns:
            处理结果
        """
        try:
            # 获取文档
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {"success": False, "error": "文档不存在"}
            
            # 更新状态为处理中
            document.status = "processing"
            self.db.commit()
            
            file_path = Path(document.file_path)
            if not file_path.exists():
                document.status = "failed"
                self.db.commit()
                return {"success": False, "error": "文件不存在"}
            
            # 1. 解析文档
            logger.info(f"开始解析文档: {document.filename}")
            parser = ParserFactory.create_parser(str(file_path))
            document_data = parser.parse()
            metadata = parser.extract_metadata()
            
            # 2. 提取元数据
            extracted_metadata = self.extractor.extract(document_data, str(file_path))
            metadata.update(extracted_metadata)
            
            # 3. 更新文档元数据
            document.title = metadata.get("title") or document.filename
            document.meta_data = metadata
            self.db.commit()
            
            # 4. 分块文档
            logger.info(f"开始分块文档: {document.filename}")
            chunks = self.chunker.chunk_document(document_data, metadata)
            
            # 5. 删除旧的分块（如果存在）
            self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # 6. 保存分块并生成向量
            logger.info(f"开始生成向量: {document.filename}, 分块数: {len(chunks)}")
            for chunk in chunks:
                content = chunk["content"]
                
                # 生成向量
                embedding = None
                if self.embedding_service:
                    try:
                        # 使用 embed_query 方法生成单个文本的向量
                        embedding = self.embedding_service.embed_query(content)
                    except Exception as e:
                        logger.warning(f"生成向量失败: {e}")
                
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk["chunk_index"],
                    content=content,
                    meta_data=chunk.get("metadata", {}),
                    embedding=embedding
                )
                self.db.add(chunk_record)
            
            # 7. 更新状态为完成
            document.status = "completed"
            self.db.commit()
            
            logger.info(f"文档处理完成: {document.filename}, 分块数: {len(chunks)}")
            
            return {
                "success": True,
                "chunks_count": len(chunks),
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"文档处理失败: {e}", exc_info=True)
            # 更新状态为失败
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                self.db.commit()
            return {"success": False, "error": str(e)}

