"""
Pydantic模式定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# 认证相关
class UserRegister(BaseModel):
    """用户注册模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str


class Token(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据模型"""
    username: Optional[str] = None


# 通用响应模型
class ResponseModel(BaseModel):
    """通用响应模型"""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    pagination: Optional[Dict[str, Any]] = None  # 分页信息


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(10, ge=1, le=100, description="每页数量，最大100")
    order_by: Optional[str] = Field(None, description="排序字段")
    order_desc: bool = Field(False, description="是否降序")


class FilterParams(BaseModel):
    """过滤参数"""
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件，格式: {字段名: 值}")


class ListResponse(BaseModel):
    """列表响应模型"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


