"""
缓存服务模块
提供SQL生成结果缓存、查询结果缓存等功能
"""
import hashlib
import json
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from app.core.config import settings

try:
    import redis
    REDIS_AVAILABLE = True
    logger.debug(f"Redis库导入成功，版本: {getattr(redis, '__version__', 'unknown')}")
except ImportError as e:
    REDIS_AVAILABLE = False
    logger.warning(f"Redis未安装，将使用内存缓存: {e}")
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"Redis导入时发生异常，将使用内存缓存: {e}")


class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        """
        初始化缓存服务
        
        Args:
            redis_url: Redis连接URL（可选，格式：redis://localhost:6379/0）
            default_ttl: 默认缓存过期时间（秒），默认1小时
        """
        self.default_ttl = default_ttl
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()  # 用于线程安全的缓存操作
        
        # 如果提供了Redis URL且Redis可用，使用Redis
        if redis_url and REDIS_AVAILABLE:
            try:
                # 解析Redis URL，支持密码
                safe_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
                logger.debug(f"尝试连接Redis: {safe_url}")
                
                # 尝试多种连接方式
                connection_success = False
                last_error = None
                
                # 方式1: 使用from_url（推荐方式）
                try:
                    # 解析URL，确保正确处理无密码的情况
                    from urllib.parse import urlparse
                    parsed = urlparse(redis_url)
                    # 如果URL中没有密码，且环境变量中有密码，使用环境变量
                    password = parsed.password if parsed.password else (settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None)
                    # 如果密码是空字符串，设置为 None（Redis 无密码）
                    if password == "":
                        password = None
                    
                    # 如果URL中没有密码，需要手动构建URL
                    if not parsed.password and password is None:
                        # 无密码情况，直接使用from_url
                        self.redis_client = redis.from_url(
                            redis_url, 
                            decode_responses=True,
                            socket_connect_timeout=10,
                            socket_timeout=10,
                            socket_keepalive=True,
                            retry_on_timeout=True,
                            health_check_interval=30
                        )
                    else:
                        # 有密码情况，使用from_url
                        self.redis_client = redis.from_url(
                            redis_url, 
                            decode_responses=True,
                            socket_connect_timeout=10,
                            socket_timeout=10,
                            socket_keepalive=True,
                            retry_on_timeout=True,
                            health_check_interval=30
                        )
                    # 测试连接
                    self.redis_client.ping()
                    connection_success = True
                    logger.info(f"✅ 使用Redis作为缓存后端: {safe_url}")
                except Exception as e1:
                    last_error = e1
                    logger.debug(f"Redis from_url连接失败: {type(e1).__name__}: {e1}")
                    
                    # 方式2: 尝试直接连接（不使用decode_responses）
                    try:
                        # 解析URL获取连接参数
                        from urllib.parse import urlparse
                        parsed = urlparse(redis_url)
                        # 如果 URL 中没有密码，且环境变量中有密码，使用环境变量
                        password = parsed.password if parsed.password else (settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None)
                        # 如果密码是空字符串，设置为 None（Redis 无密码）
                        if password == "":
                            password = None
                        host = parsed.hostname or '127.0.0.1'
                        port = parsed.port or 6379
                        # 优先使用 URL 中的 db，否则使用配置中的 REDIS_DB
                        db = int(parsed.path.lstrip('/')) if parsed.path and parsed.path != '/' else settings.REDIS_DB
                        
                        logger.debug(f"尝试直接连接Redis: {host}:{port}/{db}, password={'***' if password else 'None'}")
                        
                        # 直接连接Redis（无密码情况）
                        # 注意：Docker Redis可能配置了protected-mode，需要特殊处理
                        # 先尝试不使用health_check（某些Redis配置可能不支持）
                        try:
                            self.redis_client = redis.Redis(
                                host=host,
                                port=port,
                                db=db,
                                password=password,  # None 表示无密码
                                decode_responses=True,
                                socket_connect_timeout=10,
                                socket_timeout=10,
                                retry_on_timeout=True
                            )
                            # 测试连接
                            result = self.redis_client.ping()
                            if result:
                                connection_success = True
                                logger.info(f"✅ 使用Redis作为缓存后端（直接连接）: {host}:{port}/{db}")
                        except Exception as ping_error:
                            # ping失败，可能是health_check或socket_keepalive导致的问题
                            logger.debug(f"Redis连接失败，尝试简化配置: {ping_error}")
                            # 使用最简配置重试
                            self.redis_client = redis.Redis(
                                host=host,
                                port=port,
                                db=db,
                                password=password,
                                decode_responses=True,
                                socket_connect_timeout=5,
                                socket_timeout=5
                            )
                            result = self.redis_client.ping()
                            if result:
                                connection_success = True
                                logger.info(f"✅ 使用Redis作为缓存后端（简化配置）: {host}:{port}/{db}")
                    except Exception as e2:
                        last_error = e2
                        logger.debug(f"Redis直接连接也失败: {type(e2).__name__}: {e2}")
                
                if not connection_success:
                    error_msg = f"{type(last_error).__name__}: {last_error}" if last_error else "未知错误"
                    logger.warning(f"Redis连接失败，将使用内存缓存: {error_msg}。请检查Redis服务配置（可能需要密码或特殊配置）")
                    self.redis_client = None
                    
            except Exception as e:
                logger.warning(f"Redis初始化失败，将使用内存缓存: {type(e).__name__}: {e}")
                self.redis_client = None
        else:
            if not REDIS_AVAILABLE:
                logger.warning(f"使用内存缓存（Redis库未安装）。REDIS_AVAILABLE={REDIS_AVAILABLE}, redis_url={redis_url}")
            else:
                logger.info(f"使用内存缓存（Redis未配置）。REDIS_AVAILABLE={REDIS_AVAILABLE}, redis_url={redis_url}")
        
        # 如果使用内存缓存，启动定期清理任务
        if self.redis_client is None:
            self._start_cleanup_task()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            缓存键字符串
        """
        # 将参数序列化为JSON字符串
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        
        # 使用SHA256生成缓存键（更安全，避免MD5冲突）
        key_hash = hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"从Redis获取缓存失败: {e}")
                return None
        else:
            # 内存缓存（线程安全）
            with self._cache_lock:
                if key in self.memory_cache:
                    cache_item = self.memory_cache[key]
                    # 检查是否过期
                    if datetime.now() < cache_item.get("expires_at", datetime.max):
                        return cache_item.get("value")
                    else:
                        # 已过期，删除
                        del self.memory_cache[key]
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None则使用默认TTL
            
        Returns:
            是否设置成功
        """
        ttl = ttl or self.default_ttl
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, ensure_ascii=False, default=str)
                )
                return True
            except Exception as e:
                logger.error(f"设置Redis缓存失败: {e}")
                return False
        else:
            # 内存缓存（线程安全）
            with self._cache_lock:
                expires_at = datetime.now() + timedelta(seconds=ttl)
                self.memory_cache[key] = {
                    "value": value,
                    "expires_at": expires_at
                }
                # 限制内存缓存大小（最多保留1000个键）
                if len(self.memory_cache) > 1000:
                    # 删除最旧的缓存项
                    oldest_key = min(
                        self.memory_cache.keys(),
                        key=lambda k: self.memory_cache[k].get("expires_at", datetime.min)
                    )
                    del self.memory_cache[oldest_key]
            return True
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"删除Redis缓存失败: {e}")
                return False
        else:
            # 内存缓存（线程安全）
            with self._cache_lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            return True
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        清空缓存
        
        Args:
            pattern: 键模式（仅Redis支持），如果为None则清空所有
            
        Returns:
            删除的键数量
        """
        if self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        return self.redis_client.delete(*keys)
                else:
                    # 清空当前数据库
                    self.redis_client.flushdb()
                    return -1  # 表示清空了所有
            except Exception as e:
                logger.error(f"清空Redis缓存失败: {e}")
                return 0
        else:
            if pattern:
                # 内存缓存不支持模式匹配，只支持精确匹配
                count = 0
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    count += 1
                return count
            else:
                # 内存缓存（线程安全）
                with self._cache_lock:
                    count = len(self.memory_cache)
                    self.memory_cache.clear()
                return count
    
    def _cleanup_expired(self):
        """
        清理过期的缓存项（内部方法）
        """
        if self.redis_client is not None:
            return  # Redis自动处理过期
        
        with self._cache_lock:
            now = datetime.now()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if now >= item.get("expires_at", datetime.max)
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")
    
    def _start_cleanup_task(self):
        """
        启动定期清理任务（仅用于内存缓存）
        """
        def cleanup_worker():
            """后台清理工作线程"""
            import time
            while True:
                try:
                    time.sleep(300)  # 每5分钟清理一次
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"清理过期缓存时出错: {e}")
        
        # 启动后台线程
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True, name="CacheCleanup")
        cleanup_thread.start()
        logger.debug("已启动内存缓存定期清理任务（每5分钟）")


# 全局缓存服务实例（延迟初始化）
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    获取全局缓存服务实例
    
    Returns:
        缓存服务实例
    """
    global _cache_service
    if _cache_service is None:
        from app.core.config import settings
        redis_url = getattr(settings, 'REDIS_URL', None)
        cache_ttl = getattr(settings, 'CACHE_TTL', 3600)
        
        logger.debug(f"初始化缓存服务: REDIS_AVAILABLE={REDIS_AVAILABLE}, redis_url={redis_url}")
        
        # 如果Redis URL为空，尝试构建默认URL
        if not redis_url:
            redis_host = "127.0.0.1"
            redis_port = 6379
            redis_db = getattr(settings, 'REDIS_DB', 0)
            redis_password = getattr(settings, 'REDIS_PASSWORD', '')
            
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            
            logger.debug(f"构建默认Redis URL: {redis_url}")
        
        _cache_service = CacheService(redis_url=redis_url, default_ttl=cache_ttl)
    return _cache_service

