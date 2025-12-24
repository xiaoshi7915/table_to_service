"""
Google Drive 数据源
定时扫描Google Drive中的文件
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("google-api-python-client 未安装，Google Drive 数据源将不可用")

from .base_source import BaseSource


class GoogleDriveSource(BaseSource):
    """Google Drive 数据源"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not GOOGLE_AVAILABLE:
            raise ImportError("google-api-python-client 未安装，请安装 google-api-python-client")
        
        self.credentials_path = config.get("credentials_path")  # OAuth2 凭证文件路径
        self.token_path = config.get("token_path")  # Token 保存路径
        self.folder_id = config.get("folder_id")  # 要扫描的文件夹ID（可选）
        self.supported_mime_types = config.get("supported_mime_types", [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
            "application/msword",  # DOC
            "text/markdown",
            "text/html",
            "text/plain",
        ])
        
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """认证并创建 Drive API 服务"""
        creds = None
        
        # 尝试加载已保存的 token
        if self.token_path:
            try:
                import pickle
                import os
                if os.path.exists(self.token_path):
                    with open(self.token_path, 'rb') as token:
                        creds = pickle.load(token)
            except Exception as e:
                logger.warning(f"加载 token 失败: {e}")
        
        # 如果没有有效的凭证，进行 OAuth2 流程
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path:
                    raise ValueError("Google Drive 凭证文件路径未配置")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 保存凭证供下次使用
            if self.token_path:
                try:
                    import pickle
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    logger.warning(f"保存 token 失败: {e}")
        
        # 创建 Drive API 服务
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive 认证成功")
    
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
        if not self.service:
            return []
        
        files = []
        
        try:
            # 构建查询
            query = "trashed=false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            
            # 添加 MIME 类型过滤
            mime_type_filters = " or ".join([f"mimeType='{mime}'" for mime in self.supported_mime_types])
            query += f" and ({mime_type_filters})"
            
            # 列出文件
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime, webViewLink)"
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                files.append({
                    "file_path": f"gdrive://{item['id']}",
                    "file_id": item['id'],
                    "filename": item['name'],
                    "mime_type": item.get('mimeType', ''),
                    "file_size": int(item.get('size', 0)) if item.get('size') else 0,
                    "modified_time": item.get('modifiedTime'),
                    "created_time": item.get('createdTime'),
                    "web_view_link": item.get('webViewLink'),
                })
            
            # 排序（按修改时间倒序）
            files.sort(key=lambda x: x.get("modified_time") or "", reverse=True)
            
            # 分页
            if offset:
                files = files[offset:]
            if limit:
                files = files[:limit]
            
            return files
        except HttpError as e:
            logger.error(f"读取 Google Drive 文件列表失败: {e}")
            return []
    
    def watch(self, callback) -> None:
        """
        监听文件变更
        
        注意：Google Drive 支持 Push Notifications，但需要配置 Webhook
        这里实现简化的轮询方式
        """
        logger.warning("Google Drive 文件监听未完全实现，建议使用 Push Notifications")
        # TODO: 实现 Google Drive Push Notifications
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """
        下载文件到本地
        
        Args:
            file_id: Google Drive 文件ID
            local_path: 本地保存路径
            
        Returns:
            是否成功
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as f:
                from googleapiclient.http import MediaIoBaseDownload
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            return True
        except Exception as e:
            logger.error(f"下载 Google Drive 文件失败 {file_id}: {e}")
            return False

