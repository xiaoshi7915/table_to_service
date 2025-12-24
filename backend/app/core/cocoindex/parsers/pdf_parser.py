"""
PDF 文档解析器
支持文本提取和图片提取
"""
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger

from .base_parser import BaseParser

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("pypdf 未安装，PDF 解析功能将不可用")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFParser(BaseParser):
    """PDF 文档解析器"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        if not PYPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE and not PYMUPDF_AVAILABLE:
            raise ImportError("PDF 解析库未安装，请安装 pypdf、pdfplumber 或 PyMuPDF")
    
    def parse(self) -> Dict[str, Any]:
        """解析 PDF 文档"""
        text_content = []
        pages = []
        metadata = {}
        
        # 优先使用 PyMuPDF（性能最好）
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(self.file_path)
                metadata = doc.metadata
                for page_num, page in enumerate(doc, 1):
                    page_text = page.get_text()
                    text_content.append(page_text)
                    pages.append({
                        "page_number": page_num,
                        "text": page_text,
                        "bbox": page.rect
                    })
                doc.close()
                logger.info(f"使用 PyMuPDF 解析 PDF: {len(pages)} 页")
            except Exception as e:
                logger.warning(f"PyMuPDF 解析失败，尝试其他方法: {e}")
                if not PDFPLUMBER_AVAILABLE and not PYPDF_AVAILABLE:
                    raise
        
        # 备用方案1：使用 pdfplumber（提取质量好）
        if not pages and PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(self.file_path) as pdf:
                    metadata = pdf.metadata or {}
                    for page_num, page in enumerate(pdf.pages, 1):
                        page_text = page.extract_text() or ""
                        text_content.append(page_text)
                        pages.append({
                            "page_number": page_num,
                            "text": page_text,
                            "bbox": page.bbox if hasattr(page, 'bbox') else None
                        })
                logger.info(f"使用 pdfplumber 解析 PDF: {len(pages)} 页")
            except Exception as e:
                logger.warning(f"pdfplumber 解析失败，尝试 pypdf: {e}")
        
        # 备用方案2：使用 pypdf（基础功能）
        if not pages and PYPDF_AVAILABLE:
            try:
                with open(self.file_path, 'rb') as file:
                    pdf_reader = pypdf.PdfReader(file)
                    metadata = pdf_reader.metadata or {}
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text() or ""
                        text_content.append(page_text)
                        pages.append({
                            "page_number": page_num,
                            "text": page_text
                        })
                logger.info(f"使用 pypdf 解析 PDF: {len(pages)} 页")
            except Exception as e:
                logger.error(f"PDF 解析失败: {e}")
                raise
        
        if not pages:
            raise ValueError("无法解析 PDF 文档，所有解析方法都失败了")
        
        full_text = "\n\n".join(text_content)
        
        return {
            "text": full_text,
            "metadata": self._normalize_metadata(metadata),
            "pages": pages,
        }
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取 PDF 元数据"""
        metadata = {}
        
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(self.file_path)
                metadata = doc.metadata
                doc.close()
            except Exception:
                pass
        
        if not metadata and PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(self.file_path) as pdf:
                    metadata = pdf.metadata or {}
            except Exception:
                pass
        
        if not metadata and PYPDF_AVAILABLE:
            try:
                with open(self.file_path, 'rb') as file:
                    pdf_reader = pypdf.PdfReader(file)
                    metadata = pdf_reader.metadata or {}
            except Exception:
                pass
        
        return self._normalize_metadata(metadata)
    
    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """规范化元数据"""
        normalized = {
            "title": metadata.get("title") or metadata.get("/Title"),
            "author": metadata.get("author") or metadata.get("/Author"),
            "subject": metadata.get("subject") or metadata.get("/Subject"),
            "creator": metadata.get("creator") or metadata.get("/Creator"),
            "producer": metadata.get("producer") or metadata.get("/Producer"),
            "creation_date": metadata.get("creation_date") or metadata.get("/CreationDate"),
            "modification_date": metadata.get("modification_date") or metadata.get("/ModDate"),
        }
        # 清理 None 值
        return {k: v for k, v in normalized.items() if v is not None}
    
    @classmethod
    def supports(cls, file_path: str) -> bool:
        """检查是否支持 PDF 文件"""
        return Path(file_path).suffix.lower() in ['.pdf']

