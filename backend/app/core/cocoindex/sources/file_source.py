"""
文件数据源
用于监听文档上传和文件系统变更
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger
import hashlib

from .base_source import BaseSource
# 延迟导入 FileWatcher，避免循环导入


class FileSource(BaseSource):
    """文件数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.storage_path = Path(config.get("storage_path", ""))
        self.supported_extensions = config.get("supported_extensions", [".pdf", ".doc", ".docx", ".md", ".html", ".txt"])
        
        if not self.storage_path:
            raise ValueError("文件存储路径未配置")
        
        # 确保目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def read(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        读取文件列表
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            文件信息列表
        """
        files = []
        
        # 扫描存储目录
        for file_path in self.storage_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # 检查文件扩展名
            if file_path.suffix.lower() not in self.supported_extensions:
                continue
            
            try:
                stat = file_path.stat()
                files.append({
                    "file_path": str(file_path),
                    "filename": file_path.name,
                    "file_size": stat.st_size,
                    "file_type": file_path.suffix.lower(),
                    "modified_time": datetime.fromtimestamp(stat.st_mtime),
                    "created_time": datetime.fromtimestamp(stat.st_ctime),
                })
            except Exception as e:
                logger.warning(f"读取文件信息失败 {file_path}: {e}")
                continue
        
        # 排序（按修改时间倒序）
        files.sort(key=lambda x: x["modified_time"], reverse=True)
        
        # 分页
        if offset:
            files = files[offset:]
        if limit:
            files = files[:limit]
        
        return files
    
    def watch(self, callback) -> None:
        """
        监听文件变更（使用 watchdog）
        
        Args:
            callback: 变更回调函数，接收 (operation, file_path) 参数
        """
        try:
            from app.core.cocoindex.sync.file_watcher import FileWatcher
            
            watcher = FileWatcher(
                watch_path=str(self.storage_path),
                callback=callback,
                supported_extensions=self.supported_extensions
            )
            watcher.start()
            logger.info(f"文件系统监听已启动: {self.storage_path}")
        except ImportError:
            logger.warning("watchdog 未安装，文件系统监听不可用，将使用轮询方式")
        except Exception as e:
            logger.error(f"启动文件系统监听失败: {e}")
            logger.warning("降级到轮询方式")
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")
    
    def get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

