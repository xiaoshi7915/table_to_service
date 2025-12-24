"""
文档数据转换器
将文档分块转换为 Document 格式
"""
from typing import Dict, Any, List
from loguru import logger

from .base_transformer import BaseTransformer


class DocumentTransformer(BaseTransformer):
    """文档数据转换器"""
    
    def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        转换文档数据
        
        Args:
            data: 文档数据，包含 chunks 列表
            
        Returns:
            Document 列表（每个分块一个 Document）
        """
        chunks = data.get("chunks", [])
        document_metadata = data.get("metadata", {})
        
        documents = []
        
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_metadata = chunk.get("metadata", {})
            
            # 合并文档元数据和分块元数据
            merged_metadata = {
                **document_metadata,
                **chunk_metadata,
                "source_type": "document",
                "chunk_index": chunk.get("chunk_index"),
                "document_id": data.get("document_id"),
            }
            
            embedding = self.generate_embedding(content) if content else None
            
            documents.append({
                "content": content,
                "metadata": merged_metadata,
                "embedding": embedding,
            })
        
        return documents

