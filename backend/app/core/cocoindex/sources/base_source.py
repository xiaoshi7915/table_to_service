"""
基础数据源类
定义所有数据源的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime


class BaseSource(ABC):
    """数据源基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据源
        
        Args:
            config: 数据源配置字典
        """
        self.config = config
        self.source_type = config.get("source_type", "unknown")
        self.name = config.get("name", "unnamed")
    
    @abstractmethod
    def read(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        读取数据
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            数据记录列表
        """
        pass
    
    @abstractmethod
    def watch(self, callback) -> None:
        """
        监听数据变更（CDC）
        
        Args:
            callback: 变更回调函数，接收 (operation, record) 参数
                     operation: 'insert', 'update', 'delete'
                     record: 数据记录
        """
        pass
    
    @abstractmethod
    def get_last_sync_time(self) -> Optional[datetime]:
        """
        获取最后同步时间
        
        Returns:
            最后同步时间，如果从未同步则返回 None
        """
        pass
    
    @abstractmethod
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """
        更新最后同步时间
        
        Args:
            sync_time: 同步时间
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        return {
            "source_type": self.source_type,
            "name": self.name,
            "config": self.config
        }

