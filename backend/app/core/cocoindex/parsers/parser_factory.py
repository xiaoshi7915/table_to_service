"""
文档解析器工厂
根据文件类型自动选择合适的解析器
"""
from typing import Optional
from pathlib import Path
from loguru import logger

from .base_parser import BaseParser
from .pdf_parser import PDFParser
from .doc_parser import DOCParser
from .markdown_parser import MarkdownParser
from .html_parser import HTMLParser
from .text_parser import TextParser


class ParserFactory:
    """文档解析器工厂"""
    
    # 注册所有解析器
    _parsers = [
        PDFParser,
        DOCParser,
        MarkdownParser,
        HTMLParser,
        TextParser,
    ]
    
    @classmethod
    def create_parser(cls, file_path: str) -> BaseParser:
        """
        创建合适的解析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            文档解析器实例
            
        Raises:
            ValueError: 如果不支持该文件类型
        """
        file_path_obj = Path(file_path)
        suffix = file_path_obj.suffix.lower()
        
        # 尝试每个解析器
        for parser_class in cls._parsers:
            try:
                if parser_class.supports(file_path):
                    return parser_class(file_path)
            except Exception as e:
                logger.debug(f"解析器 {parser_class.__name__} 不支持文件 {file_path}: {e}")
                continue
        
        # 如果没有找到合适的解析器，尝试使用文本解析器作为后备
        logger.warning(f"未找到合适的解析器，使用文本解析器作为后备: {file_path}")
        try:
            return TextParser(file_path)
        except Exception as e:
            raise ValueError(f"无法解析文件 {file_path}: {e}")
    
    @classmethod
    def get_supported_extensions(cls) -> list:
        """获取所有支持的文件扩展名"""
        extensions = set()
        for parser_class in cls._parsers:
            # 这里需要从解析器的 supports 方法推断支持的扩展名
            # 或者让每个解析器提供一个类方法返回支持的扩展名
            if hasattr(parser_class, 'get_supported_extensions'):
                extensions.update(parser_class.get_supported_extensions())
            else:
                # 默认推断
                if parser_class == PDFParser:
                    extensions.add('.pdf')
                elif parser_class == DOCParser:
                    extensions.update(['.doc', '.docx'])
                elif parser_class == MarkdownParser:
                    extensions.update(['.md', '.markdown'])
                elif parser_class == HTMLParser:
                    extensions.update(['.html', '.htm', '.xhtml'])
                elif parser_class == TextParser:
                    extensions.update(['.txt', '.text', '.log'])
        
        return sorted(list(extensions))
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """检查文件类型是否支持（仅检查扩展名，不依赖文件存在性）"""
        file_path_obj = Path(file_path)
        suffix = file_path_obj.suffix.lower()
        
        # 检查是否有解析器支持该扩展名
        for parser_class in cls._parsers:
            try:
                if parser_class.supports(file_path):
                    return True
            except Exception:
                # 如果解析器的 supports 方法需要文件存在，则跳过
                continue
        
        return False

