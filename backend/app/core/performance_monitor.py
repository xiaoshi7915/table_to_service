"""
性能监控模块
跟踪各步骤耗时，记录缓存命中率，监控LLM调用时间
"""
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from loguru import logger
from contextlib import contextmanager


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "llm_calls": 0,
            "llm_total_time": 0.0,
            "sql_executions": 0,
            "sql_total_time": 0.0,
            "sql_cache_hits": 0,
            "sql_cache_misses": 0,
            "schema_loads": 0,
            "schema_total_time": 0.0,
            "schema_cache_hits": 0,
            "schema_cache_misses": 0,
        }
    
    def record_cache_hit(self, cache_type: str = "general"):
        """记录缓存命中"""
        self.metrics["cache_hits"] += 1
        if cache_type == "sql":
            self.metrics["sql_cache_hits"] += 1
        elif cache_type == "schema":
            self.metrics["schema_cache_hits"] += 1
    
    def record_cache_miss(self, cache_type: str = "general"):
        """记录缓存未命中"""
        self.metrics["cache_misses"] += 1
        if cache_type == "sql":
            self.metrics["sql_cache_misses"] += 1
        elif cache_type == "schema":
            self.metrics["schema_cache_misses"] += 1
    
    def record_llm_call(self, duration: float):
        """记录LLM调用"""
        self.metrics["llm_calls"] += 1
        self.metrics["llm_total_time"] += duration
    
    def record_sql_execution(self, duration: float, from_cache: bool = False):
        """记录SQL执行"""
        self.metrics["sql_executions"] += 1
        self.metrics["sql_total_time"] += duration
        if from_cache:
            self.record_cache_hit("sql")
        else:
            self.record_cache_miss("sql")
    
    def record_schema_load(self, duration: float, from_cache: bool = False):
        """记录Schema加载"""
        self.metrics["schema_loads"] += 1
        self.metrics["schema_total_time"] += duration
        if from_cache:
            self.record_cache_hit("schema")
        else:
            self.record_cache_miss("schema")
    
    def get_cache_hit_rate(self, cache_type: str = "general") -> float:
        """获取缓存命中率"""
        if cache_type == "sql":
            total = self.metrics["sql_cache_hits"] + self.metrics["sql_cache_misses"]
            if total == 0:
                return 0.0
            return self.metrics["sql_cache_hits"] / total
        elif cache_type == "schema":
            total = self.metrics["schema_cache_hits"] + self.metrics["schema_cache_misses"]
            if total == 0:
                return 0.0
            return self.metrics["schema_cache_hits"] / total
        else:
            total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            if total == 0:
                return 0.0
            return self.metrics["cache_hits"] / total
    
    def get_avg_llm_time(self) -> float:
        """获取平均LLM调用时间"""
        if self.metrics["llm_calls"] == 0:
            return 0.0
        return self.metrics["llm_total_time"] / self.metrics["llm_calls"]
    
    def get_avg_sql_time(self) -> float:
        """获取平均SQL执行时间"""
        if self.metrics["sql_executions"] == 0:
            return 0.0
        return self.metrics["sql_total_time"] / self.metrics["sql_executions"]
    
    def get_avg_schema_time(self) -> float:
        """获取平均Schema加载时间"""
        if self.metrics["schema_loads"] == 0:
            return 0.0
        return self.metrics["schema_total_time"] / self.metrics["schema_loads"]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "cache_hit_rate": self.get_cache_hit_rate(),
            "sql_cache_hit_rate": self.get_cache_hit_rate("sql"),
            "schema_cache_hit_rate": self.get_cache_hit_rate("schema"),
            "llm_calls": self.metrics["llm_calls"],
            "avg_llm_time": self.get_avg_llm_time(),
            "sql_executions": self.metrics["sql_executions"],
            "avg_sql_time": self.get_avg_sql_time(),
            "schema_loads": self.metrics["schema_loads"],
            "avg_schema_time": self.get_avg_schema_time(),
        }
    
    def reset(self):
        """重置指标"""
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "llm_calls": 0,
            "llm_total_time": 0.0,
            "sql_executions": 0,
            "sql_total_time": 0.0,
            "sql_cache_hits": 0,
            "sql_cache_misses": 0,
            "schema_loads": 0,
            "schema_total_time": 0.0,
            "schema_cache_hits": 0,
            "schema_cache_misses": 0,
        }


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


@contextmanager
def track_time(operation_name: str, logger_instance=None):
    """
    跟踪操作时间的上下文管理器
    
    Args:
        operation_name: 操作名称
        logger_instance: 日志记录器（可选）
    
    Yields:
        开始时间戳
    """
    start_time = time.time()
    log = logger_instance or logger
    
    try:
        yield start_time
    finally:
        duration = time.time() - start_time
        log.info(f"⏱️  {operation_name} 耗时: {duration:.3f}秒")


def track_llm_call(func: Callable):
    """
    装饰器：跟踪LLM调用时间
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            get_performance_monitor().record_llm_call(duration)
            logger.debug(f"LLM调用 {func.__name__} 耗时: {duration:.3f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"LLM调用 {func.__name__} 失败，耗时: {duration:.3f}秒，错误: {e}")
            raise
    
    return wrapper


def log_performance_summary():
    """记录性能摘要"""
    monitor = get_performance_monitor()
    summary = monitor.get_summary()
    
    logger.info("=" * 60)
    logger.info("📊 性能监控摘要")
    logger.info(f"缓存命中率: {summary['cache_hit_rate']:.2%}")
    logger.info(f"SQL缓存命中率: {summary['sql_cache_hit_rate']:.2%}")
    logger.info(f"Schema缓存命中率: {summary['schema_cache_hit_rate']:.2%}")
    logger.info(f"LLM调用次数: {summary['llm_calls']}, 平均耗时: {summary['avg_llm_time']:.3f}秒")
    logger.info(f"SQL执行次数: {summary['sql_executions']}, 平均耗时: {summary['avg_sql_time']:.3f}秒")
    logger.info(f"Schema加载次数: {summary['schema_loads']}, 平均耗时: {summary['avg_schema_time']:.3f}秒")
    logger.info("=" * 60)

