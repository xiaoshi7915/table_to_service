"""
同步服务模块
负责数据源的自动同步和增量更新
"""
from .sync_service import SyncService, sync_service
from .postgresql_cdc import PostgreSQLCDC
from .document_processor import DocumentProcessor
from .incremental_updater import IncrementalUpdater
# 延迟导入 scheduler，避免初始化错误
# from .scheduler import SyncScheduler, sync_scheduler

__all__ = [
    "SyncService",
    "sync_service",
    "PostgreSQLCDC",
    "DocumentProcessor",
    "IncrementalUpdater",
    "SyncScheduler",
    "sync_scheduler",
]

