"""
接口代理路由 - 用于处理动态接口路径
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.core.database import get_local_db
from app.models import InterfaceConfig, DatabaseConfig
from app.core.security import get_current_active_user, get_current_user
from app.api.v1.interface_executor import execute_interface_sql, get_client_ip, check_whitelist, check_blacklist, check_rate_limit
from loguru import logger

router = APIRouter(prefix="/api", tags=["接口代理"])


async def get_interface_by_path(
    proxy_path: str,
    db: Session
) -> Optional[InterfaceConfig]:
    """根据代理路径查找接口配置"""
    # 确保路径以/开头
    if not proxy_path.startswith("/"):
        proxy_path = f"/{proxy_path}"
    
    # 规范化路径：去掉/api前缀（如果存在）
    normalized_path = proxy_path
    if normalized_path.startswith("/api"):
        normalized_path = normalized_path[4:]  # 去掉 "/api"
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    
    # 查找匹配的接口配置（状态为激活或草稿）
    # 尝试多种路径格式匹配
    possible_paths = [
        normalized_path,  # /department
        f"/api{normalized_path}",  # /api/department
        proxy_path,  # 原始路径
    ]
    
    config = None
    for path in possible_paths:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.proxy_path == path,
            InterfaceConfig.status.in_(["active", "draft"])
        ).first()
        if config:
            break
    
    return config


@router.api_route("/{proxy_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_interface(
    proxy_path: str,
    request: Request,
    db: Session = Depends(get_local_db)
):
    """
    代理接口请求
    根据proxy_path动态路由到对应的接口执行器
    """
    try:
        # 查找接口配置
        interface_config = await get_interface_by_path(proxy_path, db)
        
        if not interface_config:
            raise HTTPException(
                status_code=404,
                detail=f"接口不存在: /api/{proxy_path}"
            )
        
        # 检查接口状态
        if interface_config.status == "inactive":
            raise HTTPException(
                status_code=400,
                detail="接口已禁用"
            )
        
        # 检查图形模式下的必要字段
        if interface_config.entry_mode == "graphical":
            if not interface_config.table_name:
                raise HTTPException(
                    status_code=400,
                    detail="图形模式接口配置不完整：表名为空"
                )
        
        # 获取数据库配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == interface_config.database_config_id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 获取客户端IP
        client_ip = get_client_ip(request)
        
        # 检查白名单（如果启用了白名单）
        if interface_config.enable_whitelist:
            if not check_whitelist(interface_config, client_ip):
                raise HTTPException(status_code=403, detail="您的IP不在白名单中")
        
        # 检查黑名单（如果启用了黑名单）
        if interface_config.enable_blacklist:
            if not check_blacklist(interface_config, client_ip):
                raise HTTPException(status_code=403, detail="您的IP已被加入黑名单")
        
        # 检查限流
        if not check_rate_limit(interface_config, client_ip):
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        
        # 检查认证
        current_user = None
        if interface_config.proxy_auth != "no_auth":
            try:
                current_user = await get_current_user(request, db)
            except:
                raise HTTPException(status_code=401, detail="需要认证")
        
        # 获取请求参数
        params = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_data = await request.json()
                if body_data:
                    params.update(body_data)
            except:
                pass
        
        # 合并query参数
        query_params = dict(request.query_params)
        params.update(query_params)
        
        # 处理分页参数
        page = None
        page_size = None
        if interface_config.enable_pagination:
            page = params.pop("page", params.pop("pageNumber", 1))
            page_size = params.pop("page_size", params.pop("pageSize", 10))
            try:
                page = int(page) if page else 1
                page_size = int(page_size) if page_size else 10
            except:
                page = 1
                page_size = 10
        else:
            # 移除分页参数
            params.pop("page", None)
            params.pop("pageNumber", None)
            params.pop("page_size", None)
            params.pop("pageSize", None)
        
        # 执行接口
        result = execute_interface_sql(
            interface_config,
            db_config,
            params,
            page,
            page_size,
            client_ip,
            current_user.id if current_user else None
        )
        
        # 构建响应
        return JSONResponse(
            content={
                "success": True,
                "message": "执行成功",
                "data": result
            },
            headers={
                "Content-Type": interface_config.response_format or "application/json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("代理接口执行失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"执行接口失败: {str(e)}"
        )

