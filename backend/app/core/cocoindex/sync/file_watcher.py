"""
文件系统事件监听器
使用 watchdog 监听文件变更
"""
from typing import Callable, Optional
from pathlib import Path
from loguru import logger
import threading

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog 未安装，文件系统监听功能将不可用")
    # 定义占位类，避免 NameError
    class FileSystemEventHandler:
        pass
    class FileSystemEvent:
        pass


class FileChangeHandler(FileSystemEventHandler):
    """文件变更事件处理器"""
    
    def __init__(self, callback: Callable[[str, str], None], supported_extensions: list):
        """
        初始化处理器
        
        Args:
            callback: 变更回调函数，接收 (event_type, file_path) 参数
            supported_extensions: 支持的文件扩展名列表
        """
        super().__init__()
        self.callback = callback
        self.supported_extensions = [ext.lower() for ext in supported_extensions]
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            logger.info(f"检测到新文件: {event.src_path}")
            self.callback("created", event.src_path)
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            logger.debug(f"检测到文件修改: {event.src_path}")
            self.callback("modified", event.src_path)
    
    def on_deleted(self, event):
        """文件删除事件"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            logger.info(f"检测到文件删除: {event.src_path}")
            self.callback("deleted", event.src_path)
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持"""
        path = Path(file_path)
        return path.suffix.lower() in self.supported_extensions


class FileWatcher:
    """文件系统监听器"""
    
    def __init__(
        self,
        watch_path: str,
        callback: Callable[[str, str], None],
        supported_extensions: Optional[list] = None
    ):
        """
        初始化文件监听器
        
        Args:
            watch_path: 监听路径
            callback: 变更回调函数
            supported_extensions: 支持的文件扩展名列表
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog 未安装，请安装 watchdog")
        
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.supported_extensions = supported_extensions or [".pdf", ".doc", ".docx", ".md", ".html", ".txt"]
        
        self.observer = None
        self.running = False
    
    def start(self):
        """启动监听"""
        if self.running:
            logger.warning("文件监听已在运行")
            return
        
        if not self.watch_path.exists():
            logger.warning(f"监听路径不存在，已创建: {self.watch_path}")
            self.watch_path.mkdir(parents=True, exist_ok=True)
        
        self.observer = Observer()
        event_handler = FileChangeHandler(self.callback, self.supported_extensions)
        self.observer.schedule(event_handler, str(self.watch_path), recursive=True)
        self.observer.start()
        self.running = True
        
        logger.info(f"文件系统监听已启动: {self.watch_path}")
    
    def stop(self):
        """停止监听"""
        if not self.running or not self.observer:
            return
        
        self.observer.stop()
        self.observer.join(timeout=5)
        self.running = False
        logger.info("文件系统监听已停止")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running

