"""
Azure Blob Storage 数据源
定时扫描Azure Blob容器中的文件
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

try:
    from azure.storage.blob import BlobServiceClient, ContainerClient
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-storage-blob 未安装，Azure Blob 数据源将不可用")

from .base_source import BaseSource


class AzureBlobSource(BaseSource):
    """Azure Blob Storage 数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob 未安装，请安装 azure-storage-blob")
        
        self.connection_string = config.get("connection_string")
        self.account_name = config.get("account_name")
        self.account_key = config.get("account_key")
        self.container_name = config.get("container_name")
        self.prefix = config.get("prefix", "")  # 对象前缀（可选）
        self.supported_extensions = config.get("supported_extensions", [".pdf", ".doc", ".docx", ".md", ".html", ".txt"])
        
        if not self.container_name:
            raise ValueError("Azure Blob 容器名称未配置")
        
        try:
            # 创建 Blob Service Client
            if self.connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=self.account_key)
            else:
                raise ValueError("Azure Blob 连接配置不完整")
            
            # 获取容器客户端
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # 测试连接
            self.container_client.get_container_properties()
            logger.info(f"Azure Blob 连接成功: {self.container_name}")
        except Exception as e:
            logger.error(f"Azure Blob 连接失败: {e}")
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
        if not self.container_client:
            return []
        
        files = []
        
        try:
            # 列出 Blob
            blobs = self.container_client.list_blobs(name_starts_with=self.prefix)
            
            for blob in blobs:
                # 检查文件扩展名
                if not any(blob.name.lower().endswith(ext) for ext in self.supported_extensions):
                    continue
                
                files.append({
                    "file_path": f"azure://{self.container_name}/{blob.name}",
                    "name": blob.name,
                    "filename": blob.name.split('/')[-1],
                    "file_size": blob.size,
                    "last_modified": blob.last_modified,
                    "etag": blob.etag,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
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
            logger.error(f"读取 Azure Blob 文件列表失败: {e}")
            return []
    
    def watch(self, callback) -> None:
        """
        监听文件变更
        
        注意：Azure Blob 不支持实时事件监听，需要使用 Event Grid
        这里实现简化的轮询方式
        """
        logger.warning("Azure Blob 文件监听未完全实现，建议使用 Azure Event Grid")
        # TODO: 实现 Azure Event Grid 监听
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")
    
    def download_file(self, blob_name: str, local_path: str) -> bool:
        """
        下载文件到本地
        
        Args:
            blob_name: Blob 名称
            local_path: 本地保存路径
            
        Returns:
            是否成功
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            with open(local_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            return True
        except Exception as e:
            logger.error(f"下载 Azure Blob 文件失败 {blob_name}: {e}")
            return False

