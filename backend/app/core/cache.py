"""
缓存服务模块
提供SQL生成结果缓存、查询结果缓存等功能
"""
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，将使用内存缓存")


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
        
        # 如果提供了Redis URL且Redis可用，使用Redis
        if redis_url and REDIS_AVAILABLE:
            try:
                # 解析Redis URL，支持密码
                self.redis_client = redis.from_url(
                    redis_url, 
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self.redis_client.ping()
                logger.info(f"✅ 使用Redis作为缓存后端: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
            except redis.ConnectionError as e:
                logger.warning(f"Redis连接失败，将使用内存缓存: {e}")
                self.redis_client = None
            except Exception as e:
                logger.warning(f"Redis初始化失败，将使用内存缓存: {e}")
                self.redis_client = None
        else:
            if not REDIS_AVAILABLE:
                logger.info("使用内存缓存（Redis库未安装）")
            else:
                logger.info("使用内存缓存（Redis未配置）")
    
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
        
        # 使用MD5生成短键
        key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
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
            # 内存缓存
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
            # 内存缓存
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
                count = len(self.memory_cache)
                self.memory_cache.clear()
                return count


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
        
        _cache_service = CacheService(redis_url=redis_url, default_ttl=cache_ttl)
    return _cache_service
