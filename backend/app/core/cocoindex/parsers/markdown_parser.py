"""
Markdown 文档解析器
"""
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from .base_parser import BaseParser

try:
    import markdown
    from markdown.extensions import meta
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown 未安装，Markdown 解析功能将不可用")


class MarkdownParser(BaseParser):
    """Markdown 文档解析器"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        if not MARKDOWN_AVAILABLE:
            raise ImportError("markdown 未安装，请安装 markdown")
    
    def parse(self) -> Dict[str, Any]:
        """解析 Markdown 文档"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据（如果存在）
            md = markdown.Markdown(extensions=['meta', 'codehilite', 'fenced_code'])
            html = md.convert(content)
            metadata = md.Meta if hasattr(md, 'Meta') else {}
            
            # 规范化元数据
            normalized_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list) and len(value) == 1:
                    normalized_metadata[key] = value[0]
                else:
                    normalized_metadata[key] = value
            
            # 提取标题（从内容中）
            lines = content.split('\n')
            title = None
            for line in lines[:10]:  # 检查前10行
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
                elif line.startswith('title:'):
                    title = line[6:].strip()
                    break
            
            if title:
                normalized_metadata['title'] = title
            
            return {
                "text": content,
                "html": html,  # 转换后的 HTML（可选）
                "metadata": normalized_metadata,
            }
        except Exception as e:
            logger.error(f"Markdown 文档解析失败: {e}")
            raise
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取 Markdown 文档元数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            md = markdown.Markdown(extensions=['meta'])
            md.convert(content)
            metadata = md.Meta if hasattr(md, 'Meta') else {}
            
            # 规范化元数据
            normalized = {}
            for key, value in metadata.items():
                if isinstance(value, list) and len(value) == 1:
                    normalized[key] = value[0]
                else:
                    normalized[key] = value
            
            # 如果没有元数据，尝试从内容中提取标题
            if 'title' not in normalized:
                lines = content.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if line.startswith('# '):
                        normalized['title'] = line[2:].strip()
                        break
            
            return normalized
        except Exception as e:
            logger.warning(f"提取 Markdown 元数据失败: {e}")
            return {}
    
    @classmethod
    def supports(cls, file_path: str) -> bool:
        """检查是否支持 Markdown 文档"""
        return Path(file_path).suffix.lower() in ['.md', '.markdown']

