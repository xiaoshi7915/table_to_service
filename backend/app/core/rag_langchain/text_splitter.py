"""
文本分块服务
针对中文优化的文本分割
"""
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger


class ChineseTextSplitter:
    """中文文本分块器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        """
        初始化文本分块器
        
        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠大小（字符数）
            separators: 分隔符列表（按优先级排序）
        """
        # 中文优化的分隔符（按优先级排序）
        if separators is None:
            separators = [
                "\n\n",      # 段落分隔
                "\n",        # 换行
                "。",        # 句号
                "；",        # 分号
                "，",        # 逗号
                "、",        # 顿号
                " ",         # 空格
                ""           # 字符级别
            ]
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,  # 使用字符长度（中文友好）
            is_separator_regex=False
        )
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本
        
        Args:
            text: 原始文本
            
        Returns:
            文本块列表
        """
        try:
            return self.splitter.split_text(text)
        except Exception as e:
            logger.error(f"文本分割失败: {e}", exc_info=True)
            return [text]  # 如果分割失败，返回整个文本
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分割文档（保留元数据）
        
        Args:
            documents: 文档列表，每个文档包含：
                - content: 文档内容
                - metadata: 元数据（可选）
                - id: 文档ID（可选）
                
        Returns:
            文档块列表，每个块包含：
                - content: 块内容
                - metadata: 元数据（包含chunk_index等）
        """
        chunks = []
        
        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue
            
            # 分割文本
            text_chunks = self.split_text(content)
            
            # 为每个块创建文档
            for i, chunk in enumerate(text_chunks):
                chunk_doc = {
                    "content": chunk,
                    "metadata": {
                        **doc.get("metadata", {}),
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "source_id": doc.get("id"),
                        "source_title": doc.get("title", ""),
                        "source_type": doc.get("type", "knowledge")
                    }
                }
                chunks.append(chunk_doc)
        
        logger.info(f"将 {len(documents)} 个文档分割为 {len(chunks)} 个块")
        return chunks


