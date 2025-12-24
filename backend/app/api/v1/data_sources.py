"""
数据源管理路由
用于配置和管理CocoIndex的多数据源
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_local_db
from app.models import User, DataSourceConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.cocoindex.sources.source_registry import source_registry
from app.core.cocoindex.sync.sync_service import sync_service


router = APIRouter(prefix="/api/v1/data-sources", tags=["数据源管理"])


# ==================== 请求/响应模型 ====================

class DataSourceConfigCreate(BaseModel):
    """创建数据源配置请求模型"""
    source_type: str = Field(..., description="数据源类型（postgresql、mysql、mongodb、s3、api等）")
    name: str = Field(..., description="数据源名称")
    config: Dict[str, Any] = Field(..., description="连接配置（JSON格式）")
    sync_enabled: bool = Field(True, description="是否启用同步")
    sync_frequency: Optional[int] = Field(None, description="同步频率（秒）")


class DataSourceConfigUpdate(BaseModel):
    """更新数据源配置请求模型"""
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    sync_enabled: Optional[bool] = None
    sync_frequency: Optional[int] = None


# ==================== API路由 ====================

@router.post("", response_model=ResponseModel)
@router.post("/", response_model=ResponseModel)
async def create_data_source(
    data_source_data: DataSourceConfigCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建数据源配置"""
    try:
        # 检查数据源类型是否支持
        if data_source_data.source_type not in source_registry._source_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的数据源类型: {data_source_data.source_type}"
            )
        
        # 检查名称是否已存在
        existing = db.query(DataSourceConfig).filter(
            DataSourceConfig.name == data_source_data.name,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="数据源名称已存在"
            )
        
        # 创建数据源配置
        data_source = DataSourceConfig(
            source_type=data_source_data.source_type,
            name=data_source_data.name,
            config=data_source_data.config,
            sync_enabled=data_source_data.sync_enabled,
            sync_frequency=data_source_data.sync_frequency,
            created_by=current_user.id
        )
        
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        
        # 注册到源注册表
        try:
            source = source_registry.register_from_config({
                "source_type": data_source.source_type,
                "name": data_source.name,
                **data_source.config
            })
            logger.info(f"数据源已注册: {data_source.source_type}:{data_source.name}")
        except Exception as e:
            logger.warning(f"注册数据源失败: {e}")
        
        logger.info(f"用户 {current_user.username} 创建数据源配置: {data_source.name} (ID: {data_source.id})")
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": data_source.id,
                "source_type": data_source.source_type,
                "name": data_source.name
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建数据源配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建数据源配置失败: {str(e)}"
        )


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_data_sources(
    source_type: Optional[str] = Query(None, description="数据源类型筛选"),
    sync_enabled: Optional[bool] = Query(None, description="是否启用同步"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据源列表"""
    try:
        query = db.query(DataSourceConfig).filter(DataSourceConfig.is_deleted == False)
        
        # 类型筛选
        if source_type:
            query = query.filter(DataSourceConfig.source_type == source_type)
        
        # 同步状态筛选
        if sync_enabled is not None:
            query = query.filter(DataSourceConfig.sync_enabled == sync_enabled)
        
        # 总数
        total = query.count()
        
        # 分页
        data_sources = query.order_by(DataSourceConfig.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 转换为响应格式
        data_source_list = [
            {
                "id": ds.id,
                "source_type": ds.source_type,
                "name": ds.name,
                "sync_enabled": ds.sync_enabled,
                "sync_frequency": ds.sync_frequency,
                "last_sync_at": ds.last_sync_at.isoformat() if ds.last_sync_at else None,
                "created_at": ds.created_at.isoformat() if ds.created_at else "",
                "updated_at": ds.updated_at.isoformat() if ds.updated_at else ""
            }
            for ds in data_sources
        ]
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "data_sources": data_source_list,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源列表失败: {str(e)}"
        )


@router.get("/{data_source_id}", response_model=ResponseModel)
async def get_data_source(
    data_source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据源详情"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == data_source_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": data_source.id,
                "source_type": data_source.source_type,
                "name": data_source.name,
                "config": data_source.config,
                "sync_enabled": data_source.sync_enabled,
                "sync_frequency": data_source.sync_frequency,
                "last_sync_at": data_source.last_sync_at.isoformat() if data_source.last_sync_at else None,
                "created_at": data_source.created_at.isoformat() if data_source.created_at else "",
                "updated_at": data_source.updated_at.isoformat() if data_source.updated_at else ""
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据源详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源详情失败: {str(e)}"
        )


@router.put("/{data_source_id}", response_model=ResponseModel)
async def update_data_source(
    data_source_id: int,
    data_source_data: DataSourceConfigUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新数据源配置"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == data_source_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        # 更新字段
        update_data = {}
        if data_source_data.name is not None:
            update_data["name"] = data_source_data.name
        if data_source_data.config is not None:
            update_data["config"] = data_source_data.config
        if data_source_data.sync_enabled is not None:
            update_data["sync_enabled"] = data_source_data.sync_enabled
        if data_source_data.sync_frequency is not None:
            update_data["sync_frequency"] = data_source_data.sync_frequency
        
        # 执行更新
        db.query(DataSourceConfig).filter(DataSourceConfig.id == data_source_id).update(update_data)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 更新数据源配置: {data_source.name} (ID: {data_source_id})")
        
        return ResponseModel(
            success=True,
            message="更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新数据源配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新数据源配置失败: {str(e)}"
        )


@router.delete("/{data_source_id}", response_model=ResponseModel)
async def delete_data_source(
    data_source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除数据源配置（软删除）"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == data_source_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        # 软删除
        data_source.is_deleted = True
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除数据源配置: {data_source.name} (ID: {data_source_id})")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除数据源配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除数据源配置失败: {str(e)}"
        )


@router.post("/{data_source_id}/sync", response_model=ResponseModel)
async def trigger_sync(
    data_source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """手动触发数据源同步"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == data_source_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        # 触发同步
        result = sync_service.start_sync(data_source.source_type, data_source.name)
        
        # 更新最后同步时间
        if result.get("success"):
            data_source.last_sync_at = db.query(db.func.now()).scalar()
            db.commit()
        
        return ResponseModel(
            success=result.get("success", False),
            message=result.get("message", "同步完成"),
            data=result.get("result")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发同步失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发同步失败: {str(e)}"
        )


@router.get("/{data_source_id}/sync-status", response_model=ResponseModel)
async def get_sync_status(
    data_source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据源同步状态"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == data_source_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据源不存在"
            )
        
        # 获取同步状态
        status_info = sync_service.get_sync_status(data_source.source_type, data_source.name)
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "data_source_id": data_source_id,
                "source_type": data_source.source_type,
                "name": data_source.name,
                "sync_enabled": data_source.sync_enabled,
                "last_sync_at": data_source.last_sync_at.isoformat() if data_source.last_sync_at else None,
                "sync_status": status_info
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步状态失败: {str(e)}"
        )

