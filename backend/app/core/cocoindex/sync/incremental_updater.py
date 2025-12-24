"""
增量更新引擎
只处理变更的数据，避免全量重建
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import hashlib
import json

from app.core.cocoindex.sources.base_source import BaseSource


class IncrementalUpdater:
    """增量更新引擎"""
    
    def __init__(self, source: BaseSource):
        """
        初始化增量更新引擎
        
        Args:
            source: 数据源
        """
        self.source = source
    
    def get_changed_records(
        self,
        last_sync_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取变更的记录
        
        Args:
            last_sync_time: 最后同步时间
            limit: 限制返回数量
            
        Returns:
            变更的记录列表
        """
        if not last_sync_time:
            # 如果没有最后同步时间，返回所有记录
            return self.source.read(limit=limit)
        
        # 根据数据源类型实现不同的变更检测逻辑
        # 优先使用数据源提供的增量读取方法
        source_type = getattr(self.source, 'source_type', None) or self.source.config.get('source_type', 'unknown')
        
        # 对于 PostgreSQL，可以使用 updated_at 字段进行增量查询
        if source_type == 'postgresql' and hasattr(self.source, 'read'):
            # 尝试使用数据源的增量读取方法
            try:
                # 如果数据源支持增量读取，使用它
                if hasattr(self.source, 'read_incremental'):
                    return self.source.read_incremental(last_sync_time, limit=limit)
                
                # 否则，使用带时间过滤的读取
                all_records = self.source.read(limit=limit * 2 if limit else None)
            except Exception as e:
                logger.warning(f"使用增量读取失败: {e}，降级到全量读取")
                all_records = self.source.read(limit=limit * 2 if limit else None)
        else:
            # 其他数据源，使用全量读取后过滤
            all_records = self.source.read(limit=limit * 2 if limit else None)
        
        # 过滤变更的记录（基于时间戳或内容哈希）
        changed_records = []
        for record in all_records:
            # 检查更新时间
            updated_at = record.get("updated_at") or record.get("modified_time") or record.get("last_modified")
            if updated_at:
                if isinstance(updated_at, str):
                    try:
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    except Exception:
                        continue
                
                if updated_at > last_sync_time:
                    changed_records.append(record)
            else:
                # 如果没有时间戳，使用内容哈希检测变更
                content_hash = self._calculate_content_hash(record)
                if content_hash != record.get("_last_hash"):
                    changed_records.append(record)
                    record["_last_hash"] = content_hash
        
        return changed_records[:limit] if limit else changed_records
    
    def _calculate_content_hash(self, record: Dict[str, Any]) -> str:
        """计算记录的内容哈希"""
        # 排除元数据字段
        content_fields = {k: v for k, v in record.items() if not k.startswith("_")}
        content_str = json.dumps(content_fields, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def mark_as_synced(self, records: List[Dict[str, Any]], sync_time: datetime):
        """
        标记记录为已同步
        
        Args:
            records: 已同步的记录列表
            sync_time: 同步时间
        """
        # 更新最后同步时间
        self.source.update_last_sync_time(sync_time)
        
        # 可以在这里记录已同步的记录ID，用于去重
        logger.debug(f"标记 {len(records)} 条记录为已同步")

