"""
文档分块器
基于语义和长度的智能分块
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.cocoindex.config import cocoindex_config


class DocumentChunker:
    """文档分块器"""
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        preserve_structure: bool = True
    ):
        """
        初始化分块器
        
        Args:
            chunk_size: 分块大小（tokens），默认使用配置值
            chunk_overlap: 分块重叠大小（tokens），默认使用配置值
            preserve_structure: 是否保留文档结构信息（章节、段落等）
        """
        self.chunk_size = chunk_size or cocoindex_config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or cocoindex_config.CHUNK_OVERLAP
        self.preserve_structure = preserve_structure
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        将文本分割成块
        
        Args:
            text: 要分割的文本
            metadata: 文档元数据
            
        Returns:
            分块列表，每个分块包含：
            {
                "content": str,  # 分块内容
                "chunk_index": int,  # 分块序号
                "metadata": dict,  # 分块元数据（页码、章节等）
            }
        """
        if not text or not text.strip():
            return []
        
        # 如果文本很短，直接返回单个块
        if len(text) < self.chunk_size * 3:  # 粗略估算：1 token ≈ 3-4 字符
            return [{
                "content": text.strip(),
                "chunk_index": 0,
                "metadata": metadata or {}
            }]
        
        chunks = []
        
        if self.preserve_structure:
            # 尝试基于语义边界分块（段落、章节等）
            chunks = self._chunk_by_structure(text, metadata)
        
        # 如果结构分块失败或未启用，使用固定长度分块
        if not chunks:
            chunks = self._chunk_by_length(text, metadata)
        
        return chunks
    
    def _chunk_by_structure(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """基于文档结构分块"""
        chunks = []
        
        # 按段落分割（双换行）
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para) // 3  # 粗略估算 tokens
            
            # 如果单个段落就超过块大小，需要进一步分割
            if para_size > self.chunk_size:
                # 先保存当前块
                if current_chunk:
                    chunks.append({
                        "content": "\n\n".join(current_chunk),
                        "chunk_index": chunk_index,
                        "metadata": metadata or {}
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                # 分割大段落
                para_chunks = self._split_long_paragraph(para)
                for para_chunk in para_chunks:
                    chunks.append({
                        "content": para_chunk,
                        "chunk_index": chunk_index,
                        "metadata": metadata or {}
                    })
                    chunk_index += 1
            else:
                # 检查是否可以添加到当前块
                if current_size + para_size > self.chunk_size and current_chunk:
                    # 保存当前块
                    chunks.append({
                        "content": "\n\n".join(current_chunk),
                        "chunk_index": chunk_index,
                        "metadata": metadata or {}
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                # 添加段落到当前块
                current_chunk.append(para)
                current_size += para_size
        
        # 保存最后一个块
        if current_chunk:
            chunks.append({
                "content": "\n\n".join(current_chunk),
                "chunk_index": chunk_index,
                "metadata": metadata or {}
            })
        
        return chunks
    
    def _chunk_by_length(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """基于固定长度分块"""
        chunks = []
        
        # 转换为字符数（粗略估算：1 token ≈ 3-4 字符）
        char_chunk_size = self.chunk_size * 3
        char_overlap = self.chunk_overlap * 3
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + char_chunk_size
            
            # 尝试在句号、问号、感叹号处截断
            if end < len(text):
                # 向后查找句子结束符
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in '。！？\n':
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "metadata": metadata or {}
                })
                chunk_index += 1
            
            # 移动到下一个块的起始位置（考虑重叠）
            start = end - char_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """分割超长段落"""
        chunks = []
        char_chunk_size = self.chunk_size * 3
        
        # 按句子分割
        sentences = paragraph.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n')
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence) // 3
            
            if current_size + sentence_size > char_chunk_size and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks
    
    def chunk_document(
        self,
        document_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        分块文档数据
        
        Args:
            document_data: 文档数据（来自解析器）
            metadata: 文档元数据
            
        Returns:
            分块列表
        """
        text = document_data.get("text", "")
        doc_metadata = document_data.get("metadata", {})
        
        # 合并元数据
        if metadata:
            merged_metadata = {**doc_metadata, **metadata}
        else:
            merged_metadata = doc_metadata
        
        # 如果有页面信息，保留在元数据中
        if "pages" in document_data:
            merged_metadata["has_pages"] = True
            merged_metadata["total_pages"] = len(document_data["pages"])
        
        chunks = self.chunk_text(text, merged_metadata)
        
        # 为每个分块添加页面信息（如果可用）
        if "pages" in document_data and chunks:
            self._add_page_info(chunks, document_data["pages"])
        
        return chunks
    
    def _add_page_info(
        self,
        chunks: List[Dict[str, Any]],
        pages: List[Dict[str, Any]]
    ):
        """为分块添加页面信息"""
        # 简单的页面映射：根据内容位置估算页面
        # 这是一个简化实现，实际应用中可能需要更精确的映射
        total_chars = sum(len(chunk["content"]) for chunk in chunks)
        if total_chars == 0:
            return
        
        current_pos = 0
        for chunk in chunks:
            chunk_start = current_pos
            chunk_end = current_pos + len(chunk["content"])
            
            # 估算页面范围
            start_page = None
            end_page = None
            
            page_chars = 0
            for i, page in enumerate(pages, 1):
                page_text = page.get("text", "")
                page_start = page_chars
                page_end = page_chars + len(page_text)
                
                if start_page is None and chunk_start < page_end:
                    start_page = i
                
                if chunk_end <= page_end:
                    end_page = i
                    break
                
                page_chars = page_end
            
            if start_page:
                chunk["metadata"]["start_page"] = start_page
            if end_page:
                chunk["metadata"]["end_page"] = end_page
            
            current_pos = chunk_end

