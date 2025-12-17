"""
表配置路由（兼容旧接口）
注意：当前系统主要使用 interface_configs，此路由用于兼容前端调用
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_local_db
from models import User, InterfaceConfig, DatabaseConfig
from schemas import ResponseModel
from auth import get_current_active_user
from loguru import logger

router = APIRouter(prefix="/api/v1/table-configs", tags=["表配置"])


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_configs(
    enabled: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """
    获取表配置列表
    注意：此接口返回基于 interface_configs 的数据，用于兼容前端
    """
    try:
        # 查询接口配置，转换为表配置格式
        query = db.query(InterfaceConfig).filter(InterfaceConfig.user_id == current_user.id)
        
        # 如果指定了 enabled 参数，根据 status 过滤
        if enabled is not None:
            if enabled:
                query = query.filter(InterfaceConfig.status == "active")
            else:
                query = query.filter(InterfaceConfig.status != "active")
        
        configs = query.order_by(InterfaceConfig.created_at.desc()).all()
        
        result = []
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
            
            # 转换为表配置格式
            result.append({
                "id": config.id,
                "name": config.table_name or config.interface_name,  # 使用表名或接口名
                "database": db_config.name if db_config else "",
                "database_id": config.database_config_id,
                "enabled": config.status == "active",
                "status": config.status,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except Exception as e:
        logger.error(f"获取表配置列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表配置列表失败: {str(e)}"
        )

