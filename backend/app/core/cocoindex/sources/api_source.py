"""
API 数据源（REST/GraphQL）
通过轮询或 Webhook 方式获取数据
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import httpx
import json

from .base_source import BaseSource


class APISource(BaseSource):
    """API 数据源（REST/GraphQL）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.api_type = config.get("api_type", "rest")  # rest 或 graphql
        self.method = config.get("method", "GET")  # GET 或 POST
        self.headers = config.get("headers", {})
        self.auth_type = config.get("auth_type")  # none, api_key, oauth, bearer
        self.auth_config = config.get("auth_config", {})
        self.query_params = config.get("query_params", {})
        self.request_body = config.get("request_body")
        self.graphql_query = config.get("graphql_query")  # GraphQL 查询语句
        
        if not self.api_url:
            raise ValueError("API URL 未配置")
        
        # 设置认证头
        self._setup_auth()
    
    def _setup_auth(self):
        """设置认证头"""
        if self.auth_type == "api_key":
            api_key = self.auth_config.get("api_key")
            key_name = self.auth_config.get("key_name", "X-API-Key")
            if api_key:
                self.headers[key_name] = api_key
        elif self.auth_type == "bearer":
            token = self.auth_config.get("token")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
        elif self.auth_type == "oauth":
            # OAuth 需要更复杂的实现，这里简化
            token = self.auth_config.get("access_token")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
    
    def read(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        读取数据
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            数据记录列表
        """
        try:
            if self.api_type == "graphql":
                return self._read_graphql(limit, offset)
            else:
                return self._read_rest(limit, offset)
        except Exception as e:
            logger.error(f"API 数据读取失败: {e}")
            return []
    
    def _read_rest(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """读取 REST API 数据"""
        try:
            # 添加分页参数
            params = self.query_params.copy()
            if limit:
                params["limit"] = limit
            if offset:
                params["offset"] = offset
            
            # 发送请求
            with httpx.Client(timeout=30.0) as client:
                if self.method.upper() == "GET":
                    response = client.get(
                        self.api_url,
                        headers=self.headers,
                        params=params
                    )
                else:  # POST
                    body = self.request_body or {}
                    response = client.post(
                        self.api_url,
                        headers=self.headers,
                        params=params,
                        json=body
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # 尝试提取数据列表（支持多种响应格式）
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # 尝试常见的字段名
                    for key in ["data", "results", "items", "records"]:
                        if key in data and isinstance(data[key], list):
                            return data[key]
                    # 如果没有列表字段，返回整个对象
                    return [data]
                else:
                    return []
        except Exception as e:
            logger.error(f"REST API 请求失败: {e}")
            return []
    
    def _read_graphql(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """读取 GraphQL API 数据"""
        if not self.graphql_query:
            logger.warning("GraphQL 查询语句未配置")
            return []
        
        try:
            # 构建 GraphQL 请求
            query = self.graphql_query
            variables = self.query_params.copy()
            if limit:
                variables["limit"] = limit
            if offset:
                variables["offset"] = offset
            
            payload = {
                "query": query,
                "variables": variables
            }
            
            # 发送请求
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.api_url,
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                # GraphQL 响应格式：{"data": {...}}
                if isinstance(data, dict) and "data" in data:
                    result = data["data"]
                    # 尝试提取列表
                    if isinstance(result, list):
                        return result
                    elif isinstance(result, dict):
                        # 查找第一个列表字段
                        for value in result.values():
                            if isinstance(value, list):
                                return value
                    return [result]
                else:
                    return []
        except Exception as e:
            logger.error(f"GraphQL API 请求失败: {e}")
            return []
    
    def watch(self, callback) -> None:
        """
        监听数据变更
        
        注意：API 数据源通常使用轮询方式，或需要配置 Webhook
        """
        logger.warning("API 数据源监听未完全实现，建议使用轮询或 Webhook")
        # TODO: 实现 Webhook 监听或轮询机制
        pass
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """获取最后同步时间"""
        return self.config.get("last_sync_time")
    
    def update_last_sync_time(self, sync_time: datetime) -> None:
        """更新最后同步时间"""
        self.config["last_sync_time"] = sync_time
        logger.debug(f"更新最后同步时间: {sync_time}")

