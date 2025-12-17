"""
API v1 Routes Package
"""
from fastapi import APIRouter

# 创建v1 API路由器
api_router = APIRouter(prefix="/api/v1", tags=["v1"])

