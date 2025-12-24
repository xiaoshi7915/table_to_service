"""
纯文本解析器
"""
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from .base_parser import BaseParser


class TextParser(BaseParser):
    """纯文本解析器"""
    
    def parse(self) -> Dict[str, Any]:
        """解析文本文件"""
        try:
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.debug(f"使用 {encoding} 编码成功读取文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"无法使用任何编码读取文件: {self.file_path}")
            
            # 提取标题（第一行或前几行）
            lines = content.split('\n')
            title = None
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) < 200:  # 标题通常不会太长
                    title = line
                    break
            
            return {
                "text": content,
                "metadata": {
                    "title": title,
                    "line_count": len(lines),
                }
            }
        except Exception as e:
            logger.error(f"文本文件解析失败: {e}")
            raise
    
    def extract_metadata(self) -> Dict[str, Any]:
        """提取文本文件元数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            
            title = None
            for line in first_lines:
                if line and len(line) < 200:
                    title = line
                    break
            
            return {
                "title": title,
            }
        except Exception as e:
            logger.warning(f"提取文本文件元数据失败: {e}")
            return {}
    
    @classmethod
    def supports(cls, file_path: str) -> bool:
        """检查是否支持文本文件"""
        return Path(file_path).suffix.lower() in ['.txt', '.text', '.log']

