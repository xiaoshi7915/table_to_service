"""
批量处理器
用于批量处理大量数据，避免内存溢出
"""
from typing import List, Callable, Any, Optional, Dict
from loguru import logger
import time


class BatchProcessor:
    """批量处理器"""
    
    def __init__(
        self,
        batch_size: int = 100,
        max_workers: int = 4,
        retry_times: int = 3
    ):
        """
        初始化批量处理器
        
        Args:
            batch_size: 批次大小
            max_workers: 最大并发数
            retry_times: 重试次数
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.retry_times = retry_times
    
    def process(
        self,
        items: List[Any],
        processor: Callable[[List[Any]], Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        批量处理数据
        
        Args:
            items: 要处理的数据列表
            processor: 处理函数，接收一批数据，返回处理结果
            progress_callback: 进度回调函数，接收 (processed, total)
            
        Returns:
            处理结果统计
        """
        total = len(items)
        processed = 0
        success_count = 0
        failed_count = 0
        errors = []
        
        # 分批处理
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            logger.info(f"处理批次 {batch_num}/{total_batches}，大小: {len(batch)}")
            
            # 重试机制
            retry_count = 0
            batch_success = False
            
            while retry_count <= self.retry_times:
                try:
                    result = processor(batch)
                    if result.get("success", False):
                        batch_success = True
                        processed_count_in_batch = result.get("processed", len(batch))
                        success_count += processed_count_in_batch
                        break
                    else:
                        error_msg = result.get("error", "未知错误")
                        logger.warning(f"批次 {batch_num} 处理失败: {error_msg}")
                        if retry_count < self.retry_times:
                            retry_count += 1
                            time.sleep(1)  # 等待1秒后重试
                            continue
                        else:
                            failed_count += len(batch)
                            errors.append(f"批次 {batch_num}: {error_msg}")
                            break
                except Exception as e:
                    logger.error(f"批次 {batch_num} 处理异常: {e}", exc_info=True)
                    if retry_count < self.retry_times:
                        retry_count += 1
                        time.sleep(1)
                        continue
                    else:
                        failed_count += len(batch)
                        errors.append(f"批次 {batch_num}: {str(e)}")
                        break
            
            processed += len(batch)
            
            # 调用进度回调
            if progress_callback:
                progress_callback(processed, total)
        
        return {
            "total": total,
            "processed": processed,
            "success": success_count,
            "failed": failed_count,
            "errors": errors[:10]  # 只返回前10个错误
        }

