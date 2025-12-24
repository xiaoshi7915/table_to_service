"""
HTML/网页解析器
"""
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from .base_parser import BaseParser

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("beautifulsoup4 未安装，HTML 解析功能将不可用")

try:
    from readability import Document as ReadabilityDocument
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False


class HTMLParser(BaseParser):
    """HTML/网页解析器"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        if not BS4_AVAILABLE:
            raise ImportError("beautifulsoup4 未安装，请安装 beautifulsoup4")
    
    def parse(self) -> Dict[str, Any]:
        """解析 HTML 文档"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title = None
            if soup.title:
                title = soup.title.string
            elif soup.find('h1'):
                title = soup.find('h1').get_text()
            
            # 移除脚本和样式标签
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # 提取正文文本
            text = soup.get_text(separator='\n', strip=True)
            
            # 如果可用，使用 readability 提取主要内容
            main_content = text
            if READABILITY_AVAILABLE:
                try:
                    doc = ReadabilityDocument(html_content)
                    main_content = doc.summary()
                    # 再次解析提取的 HTML
                    soup_main = BeautifulSoup(main_content, 'html.parser')
                    main_content = soup_main.get_text(separator='\n', strip=True)
                except Exception as e:
                    logger.debug(f"使用 readability 提取失败，使用全部内容: {e}")
            
            # 提取元数据
            metadata = self.extract_metadata(soup)
            if title:
                metadata['title'] = title
            
            return {
                "text": main_content or text,
                "metadata": metadata,
                "full_html": html_content,  # 保留原始 HTML（可选）
            }
        except Exception as e:
            logger.error(f"HTML 文档解析失败: {e}")
            raise
    
    def extract_metadata(self, soup = None) -> Dict[str, Any]:
        """提取 HTML 文档元数据"""
        try:
            if soup is None:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')
            
            metadata = {}
            
            # 提取 meta 标签
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                content = meta.get('content')
                if name and content:
                    # 规范化名称
                    name = name.lower().replace(':', '_')
                    metadata[name] = content
            
            # 提取标题
            if soup.title:
                metadata['title'] = soup.title.string
            
            # 提取描述
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                metadata['description'] = desc_tag.get('content')
            
            return metadata
        except Exception as e:
            logger.warning(f"提取 HTML 元数据失败: {e}")
            return {}
    
    @classmethod
    def supports(cls, file_path: str) -> bool:
        """检查是否支持 HTML 文档"""
        return Path(file_path).suffix.lower() in ['.html', '.htm', '.xhtml']

