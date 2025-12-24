"""
MongoDB 数据源
使用 Change Streams 监听变更
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("pymongo 未安装，MongoDB 数据源将不可用")

from .base_source import BaseSource


class MongoDBSource(BaseSource):
    """MongoDB 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo 未安装，请安装 pymongo")
        
        self.connection_string = config.get("connection_string")
        self.database_name = config.get("database_name")
        self.collections = config.get("collections", [])  # 要监听的集合列表
        self.client = None
        self.db = None
        
        if not self.connection_string:
            raise ValueError("MongoDB 连接字符串未配置")
        if not self.database_name:
            raise ValueError("MongoDB 数据库名未配置")
        
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            # 测试连接
            self.client.admin.command('ping')
            logger.info(f"MongoDB 连接成功: {self.database_name}")
        except Exception as e:
            logger.error(f"创建 MongoDB 连接失败: {e}")
            raise
    
    def read(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        读取数据
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            collection_name: 集合名（如果指定，只读取该集合）
            
        Returns:
            数据记录列表
        """
        if not self.db:
            return []
        
        results = []
        collections_to_read = [collection_name] if collection_name else self.collections
        
        for coll_name in collections_to_read:
            try:
                collection = self.db[coll_name]
                
                # 构建查询
                query = {}
                
                # 分页
                cursor = collection.find(query)
                if offset:
                    cursor = cursor.skip(offset)
                if limit:
                    cursor = cursor.limit(limit)
                
                # 转换为列表
                for doc in cursor:
                    # 转换 ObjectId 为字符串
                    doc["_id"] = str(doc["_id"])
                    doc["_source_collection"] = coll_name  # 添加集合名标识
                    results.append(doc)
                
                logger.debug(f"从集合 {coll_name} 读取 {len(results)} 条记录")
            except Exception as e:
                logger.warning(f"读取集合 {coll_name} 失败: {e}")
                continue
        
        return results
    
    def watch(self, callback) -> None:
        """
        监听数据变更（使用 MongoDB Change Streams）
        
        Args:
            callback: 变更回调函数，接收 (operation, document) 参数
        """
        if not self.db:
            logger.warning("MongoDB 连接不可用，无法监听变更")
            return
        
        try:
            # 监听所有集合的变更
            for coll_name in self.collections:
                collection = self.db[coll_name]
                
                # 创建 Change Stream
                with collection.watch() as stream:
                    logger.info(f"开始监听集合 {coll_name} 的变更")
                    for change in stream:
                        operation = change.get("operationType")
                        document = change.get("fullDocument") or change.get("documentKey")
                        
                        if operation == "insert":
                            callback("insert", document)
                        elif operation == "update":
                            callback("update", document)
                        elif operation == "delete":
                            callback("delete", document)
        except Exception as e:
            logger.error(f"MongoDB Change Stream 监听失败: {e}")
            # 降级到轮询方式
            logger.warning("降级到轮询方式监听变更")
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        if not self.db:
            return {}
        
        try:
            collection = self.db[collection_name]
            stats = self.db.command("collStats", collection_name)
            
            return {
                "collection_name": collection_name,
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "storage_size": stats.get("storageSize", 0),
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {}
    
    def __del__(self):
        """清理资源"""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

