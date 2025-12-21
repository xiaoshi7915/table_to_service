"""
仪表板管理API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from loguru import logger
from datetime import datetime
import json

from app.core.database import get_local_db
from app.core.security import get_current_active_user
from app.models import User, Dashboard, DashboardWidget, ChatMessage
from app.schemas import ResponseModel

router = APIRouter(prefix="/api/v1/dashboards", tags=["仪表板"])


# 请求模型
class CreateDashboardRequest(BaseModel):
    """创建仪表板请求"""
    name: str
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    is_public: bool = False


class UpdateDashboardRequest(BaseModel):
    """更新仪表板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class CreateWidgetRequest(BaseModel):
    """创建组件请求"""
    widget_type: str  # chart, table
    title: str
    config: Dict[str, Any]
    position_x: int = 0
    position_y: int = 0
    width: int = 400
    height: int = 300
    message_id: Optional[int] = None  # 从消息创建组件时使用


class UpdateWidgetRequest(BaseModel):
    """更新组件请求"""
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


@router.get("", response_model=ResponseModel)
async def list_dashboards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取仪表板列表"""
    try:
        query = db.query(Dashboard).filter(
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        )
        
        # 关键词搜索
        if keyword:
            query = query.filter(Dashboard.name.like(f"%{keyword}%"))
        
        # 总数
        total = query.count()
        
        # 分页
        dashboards = query.order_by(desc(Dashboard.updated_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 构建响应数据
        dashboard_list = []
        for dashboard in dashboards:
            # 获取组件数量
            widget_count = db.query(DashboardWidget).filter(
                DashboardWidget.dashboard_id == dashboard.id
            ).count()
            
            dashboard_list.append({
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "is_public": dashboard.is_public,
                "widget_count": widget_count,
                "created_at": dashboard.created_at.isoformat(),
                "updated_at": dashboard.updated_at.isoformat()
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=dashboard_list,
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        )
        
    except Exception as e:
        logger.error(f"获取仪表板列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取仪表板列表失败: {str(e)}")


@router.post("", response_model=ResponseModel)
async def create_dashboard(
    request: CreateDashboardRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建仪表板"""
    try:
        dashboard = Dashboard(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            layout_config=json.dumps(request.layout_config, ensure_ascii=False) if request.layout_config else None,
            is_public=request.is_public
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": dashboard.id,
                "name": dashboard.name,
                "created_at": dashboard.created_at.isoformat()
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建仪表板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建仪表板失败: {str(e)}")


@router.get("/{dashboard_id}", response_model=ResponseModel)
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取仪表板详情"""
    try:
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        # 获取组件列表
        widgets = db.query(DashboardWidget).filter(
            DashboardWidget.dashboard_id == dashboard_id
        ).order_by(DashboardWidget.position_y, DashboardWidget.position_x).all()
        
        widget_list = []
        for widget in widgets:
            try:
                config = json.loads(widget.config) if widget.config else {}
            except:
                config = {}
            
            widget_list.append({
                "id": widget.id,
                "widget_type": widget.widget_type,
                "title": widget.title,
                "config": config,
                "position_x": widget.position_x,
                "position_y": widget.position_y,
                "width": widget.width,
                "height": widget.height
            })
        
        layout_config = None
        if dashboard.layout_config:
            try:
                layout_config = json.loads(dashboard.layout_config)
            except:
                pass
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "layout_config": layout_config,
                "is_public": dashboard.is_public,
                "widgets": widget_list,
                "created_at": dashboard.created_at.isoformat(),
                "updated_at": dashboard.updated_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取仪表板详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取仪表板详情失败: {str(e)}")


@router.put("/{dashboard_id}", response_model=ResponseModel)
async def update_dashboard(
    dashboard_id: int,
    request: UpdateDashboardRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新仪表板"""
    try:
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        if request.name is not None:
            dashboard.name = request.name
        if request.description is not None:
            dashboard.description = request.description
        if request.layout_config is not None:
            dashboard.layout_config = json.dumps(request.layout_config, ensure_ascii=False)
        if request.is_public is not None:
            dashboard.is_public = request.is_public
        
        db.commit()
        db.refresh(dashboard)
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={
                "id": dashboard.id,
                "name": dashboard.name
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新仪表板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新仪表板失败: {str(e)}")


@router.delete("/{dashboard_id}", response_model=ResponseModel)
async def delete_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除仪表板"""
    try:
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        if dashboard.is_deleted:
            raise HTTPException(status_code=404, detail="仪表板已被删除")
        
        # 软删除仪表板及其组件
        dashboard.is_deleted = True
        # 同时软删除所有组件
        db.query(DashboardWidget).filter(
            DashboardWidget.dashboard_id == dashboard_id,
            DashboardWidget.is_deleted == False
        ).update({"is_deleted": True}, synchronize_session=False)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除仪表板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除仪表板失败: {str(e)}")


@router.post("/{dashboard_id}/widgets", response_model=ResponseModel)
async def create_widget(
    dashboard_id: int,
    request: CreateWidgetRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """添加组件到仪表板"""
    try:
        # 验证仪表板
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        # 如果从消息创建，获取消息的图表配置
        config = request.config
        if request.message_id:
            message = db.query(ChatMessage).filter(
                ChatMessage.id == request.message_id
            ).first()
            
            if message and message.chart_config:
                try:
                    chart_config = json.loads(message.chart_config)
                    config = chart_config
                except:
                    pass
        
        widget = DashboardWidget(
            dashboard_id=dashboard_id,
            widget_type=request.widget_type,
            title=request.title,
            config=json.dumps(config, ensure_ascii=False),
            position_x=request.position_x,
            position_y=request.position_y,
            width=request.width,
            height=request.height
        )
        db.add(widget)
        db.commit()
        db.refresh(widget)
        
        return ResponseModel(
            success=True,
            message="添加组件成功",
            data={
                "id": widget.id,
                "widget_type": widget.widget_type,
                "title": widget.title
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"添加组件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加组件失败: {str(e)}")


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=ResponseModel)
async def update_widget(
    dashboard_id: int,
    widget_id: int,
    request: UpdateWidgetRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新组件"""
    try:
        # 验证仪表板
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        widget = db.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
            DashboardWidget.is_deleted == False
        ).first()
        
        if not widget:
            raise HTTPException(status_code=404, detail="组件不存在")
        
        if request.title is not None:
            widget.title = request.title
        if request.config is not None:
            widget.config = json.dumps(request.config, ensure_ascii=False)
        if request.position_x is not None:
            widget.position_x = request.position_x
        if request.position_y is not None:
            widget.position_y = request.position_y
        if request.width is not None:
            widget.width = request.width
        if request.height is not None:
            widget.height = request.height
        
        db.commit()
        db.refresh(widget)
        
        return ResponseModel(
            success=True,
            message="更新组件成功",
            data={
                "id": widget.id,
                "title": widget.title
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新组件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新组件失败: {str(e)}")


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=ResponseModel)
async def delete_widget(
    dashboard_id: int,
    widget_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除组件"""
    try:
        # 验证仪表板
        dashboard = db.query(Dashboard).filter(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == current_user.id,
            Dashboard.is_deleted == False
        ).first()
        
        if not dashboard:
            raise HTTPException(status_code=404, detail="仪表板不存在")
        
        widget = db.query(DashboardWidget).filter(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
            DashboardWidget.is_deleted == False
        ).first()
        
        if not widget:
            raise HTTPException(status_code=404, detail="组件不存在")
        
        if widget.is_deleted:
            raise HTTPException(status_code=404, detail="组件已被删除")
        
        # 软删除
        widget.is_deleted = True
        db.commit()
        
        return ResponseModel(
            success=True,
            message="删除组件成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除组件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除组件失败: {str(e)}")

