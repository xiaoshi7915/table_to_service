"""
定时同步任务调度器
使用 APScheduler 定时同步低频数据源
"""
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler 未安装，定时同步功能将不可用")

from app.core.cocoindex.sources.source_registry import source_registry
from app.core.cocoindex.sync.sync_service import sync_service
from app.core.database import get_local_db
from app.models import DataSourceConfig


class SyncScheduler:
    """同步任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler 未安装，请安装 APScheduler")
        
        self.scheduler = BackgroundScheduler()
        self.job_ids = {}
        self.running = False
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.scheduler.start()
        self.running = True
        logger.info("同步任务调度器已启动")
        
        # 加载并启动所有数据源的定时任务
        self._load_and_schedule_all()
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.scheduler.shutdown()
        self.running = False
        self.job_ids.clear()
        logger.info("同步任务调度器已停止")
    
    def _load_and_schedule_all(self):
        """加载所有数据源配置并启动定时任务"""
        try:
            # 获取数据库会话
            db_gen = get_local_db()
            db = next(db_gen)
            
            try:
                # 获取所有启用的数据源
                data_sources = db.query(DataSourceConfig).filter(
                    DataSourceConfig.is_deleted == False,
                    DataSourceConfig.sync_enabled == True,
                    DataSourceConfig.sync_frequency.isnot(None)
                ).all()
                
                for ds in data_sources:
                    self.schedule_source_sync(
                        source_type=ds.source_type,
                        source_name=ds.name,
                        sync_frequency=ds.sync_frequency
                    )
                
                logger.info(f"已加载 {len(data_sources)} 个数据源的定时同步任务")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"加载数据源配置失败: {e}")
    
    def schedule_source_sync(
        self,
        source_type: str,
        source_name: str,
        sync_frequency: int
    ):
        """
        为数据源添加定时同步任务
        
        Args:
            source_type: 数据源类型
            source_name: 数据源名称
            sync_frequency: 同步频率（秒）
        """
        job_id = f"{source_type}:{source_name}"
        
        # 如果任务已存在，先移除
        if job_id in self.job_ids:
            try:
                self.scheduler.remove_job(self.job_ids[job_id])
            except Exception as e:
                logger.warning(f"移除旧任务失败: {e}")
        
        # 添加新任务
        try:
            job = self.scheduler.add_job(
                func=self._sync_job,
                trigger=IntervalTrigger(seconds=sync_frequency),
                args=[source_type, source_name],
                id=job_id,
                replace_existing=True,
                max_instances=1  # 同一时间只运行一个实例
            )
            
            self.job_ids[job_id] = job.id
            logger.info(f"已添加定时同步任务: {job_id}, 频率: {sync_frequency}秒")
        except Exception as e:
            logger.error(f"添加定时同步任务失败: {e}")
    
    def _sync_job(self, source_type: str, source_name: str):
        """同步任务执行函数"""
        try:
            logger.info(f"执行定时同步: {source_type}:{source_name}")
            result = sync_service.start_sync(source_type, source_name)
            
            if result.get("success"):
                logger.info(f"定时同步成功: {source_type}:{source_name}")
            else:
                logger.warning(f"定时同步失败: {source_type}:{source_name}, {result.get('message')}")
        except Exception as e:
            logger.error(f"定时同步任务执行失败: {e}", exc_info=True)
    
    def remove_source_sync(self, source_type: str, source_name: str):
        """移除数据源的定时同步任务"""
        job_id = f"{source_type}:{source_name}"
        
        if job_id in self.job_ids:
            try:
                self.scheduler.remove_job(self.job_ids[job_id])
                del self.job_ids[job_id]
                logger.info(f"已移除定时同步任务: {job_id}")
            except Exception as e:
                logger.warning(f"移除定时同步任务失败: {e}")
    
    def get_scheduled_jobs(self) -> Dict[str, Any]:
        """获取所有已调度的任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return {"jobs": jobs, "count": len(jobs)}


# 全局调度器实例
sync_scheduler = SyncScheduler()

