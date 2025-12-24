"""
AWS S3 数据源
定时扫描S3存储桶中的文件
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 未安装，S3 数据源将不可用")

from .base_source import BaseSource


class S3Source(BaseSource):
    """AWS S3 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 未安装，请安装 boto3")
        
        self.bucket_name = config.get("bucket_name")
        self.prefix = config.get("prefix", "")  # 对象前缀（可选）
        self.aws_access_key_id = config.get("aws_access_key_id")
        self.aws_secret_access_key = config.get("aws_secret_access_key")
        self.region_name = config.get("region_name", "us-east-1")
        self.supported_extensions = config.get("supported_extensions", [".pdf", ".doc", ".docx", ".md", ".html", ".txt"])
        
        if not self.bucket_name:
            raise ValueError("S3 存储桶名称未配置")
        
        try:
            # 创建 S3 客户端
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            # 测试连接
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 连接成功: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS 凭证未配置")
            raise
        except ClientError as e:
            logger.error(f"S3 连接失败: {e}")
            raise
    
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
        if not self.s3_client:
            return []
        
        files = []
        
        try:
            # 列出对象
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )
            
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # 检查文件扩展名
                    if not any(key.lower().endswith(ext) for ext in self.supported_extensions):
                        continue
                    
                    files.append({
                        "file_path": f"s3://{self.bucket_name}/{key}",
                        "key": key,
                        "filename": key.split('/')[-1],
                        "file_size": obj.get('Size', 0),
                        "last_modified": obj.get('LastModified'),
                        "etag": obj.get('ETag', '').strip('"'),
                    })
            
            # 排序（按修改时间倒序）
            files.sort(key=lambda x: x.get("last_modified") or datetime.min, reverse=True)
            
            # 分页
            if offset:
                files = files[offset:]
            if limit:
                files = files[:limit]
            
            return files
        except Exception as e:
            logger.error(f"读取 S3 文件列表失败: {e}")
            return []
    
    def watch(self, callback) -> None:
        """
        监听文件变更
        
        注意：S3 不支持实时事件监听，需要使用 S3 Event Notifications + SQS/SNS
        这里实现简化的轮询方式
        """
        logger.warning("S3 文件监听未完全实现，建议使用 S3 Event Notifications + SQS")
        # TODO: 实现 S3 Event Notifications 监听
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")
    
    def download_file(self, key: str, local_path: str) -> bool:
        """
        下载文件到本地
        
        Args:
            key: S3 对象键
            local_path: 本地保存路径
            
        Returns:
            是否成功
        """
        try:
            self.s3_client.download_file(self.bucket_name, key, local_path)
            return True
        except Exception as e:
            logger.error(f"下载 S3 文件失败 {key}: {e}")
            return False

