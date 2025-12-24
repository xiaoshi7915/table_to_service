"""
基础文档解析器
定义所有解析器的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class BaseParser(ABC):
    """文档解析器基类"""
    
    def __init__(self, file_path: str):
        """
        初始化解析器
        
        Args:
            file_path: 文件路径
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        解析文档
        
        Returns:
            包含文档内容的字典：
            {
                "text": str,  # 文档文本内容
                "metadata": dict,  # 文档元数据
                "pages": list,  # 页面列表（如果适用）
            }
        """
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """
        提取文档元数据
        
        Returns:
            元数据字典，包含标题、作者、创建时间等
        """
        pass
    
    def get_file_info(self) -> Dict[str, Any]:
        """
        获取文件基本信息
        
        Returns:
            文件信息字典
        """
        stat = self.file_path.stat()
        return {
            "filename": self.file_path.name,
            "file_size": stat.st_size,
            "file_type": self.file_path.suffix.lower(),
            "modified_time": stat.st_mtime,
        }
    
    @classmethod
    @abstractmethod
    def supports(cls, file_path: str) -> bool:
        """
        检查是否支持该文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        pass

