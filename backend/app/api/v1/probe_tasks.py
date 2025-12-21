"""
探查任务管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, exists
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.database import get_local_db
from app.models import User, ProbeTask, DatabaseConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.probe.probe_executor import ProbeExecutor
from loguru import logger
import threading


router = APIRouter(prefix="/api/v1/probe-tasks", tags=["探查任务"])


def _execute_task_async(task_id: int, db: Session):
    """异步执行探查任务"""
    try:
        executor = ProbeExecutor(db)
        executor.execute_task(task_id)
    except Exception as e:
        logger.error(f"异步执行探查任务失败: {e}", exc_info=True)
        # 更新任务状态为失败
        task = db.query(ProbeTask).filter(ProbeTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_tasks(
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索关键词（任务名称、数据源名称）"),
    status_filter: Optional[str] = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取探查任务列表（支持搜索、分页、筛选）"""
    try:
        query = db.query(ProbeTask).filter(ProbeTask.user_id == current_user.id)
        
        # 搜索
        if search:
            query = query.join(DatabaseConfig, ProbeTask.database_config_id == DatabaseConfig.id).filter(
                or_(
                    ProbeTask.task_name.like(f"%{search}%"),
                    DatabaseConfig.name.like(f"%{search}%")
                )
            )
        
        # 状态筛选
        if status_filter:
            query = query.filter(ProbeTask.status == status_filter)
        
        # 排序
        query = query.order_by(ProbeTask.created_at.desc())
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()
        
        # 获取关联的数据源信息
        result = []
        for task in tasks:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == task.database_config_id).first()
            result.append({
                "id": task.id,
                "task_name": task.task_name,
                "database_config_id": task.database_config_id,
                "database_config_name": db_config.name if db_config else "",
                "db_type": db_config.db_type if db_config else "",
                "probe_mode": task.probe_mode,
                "probe_level": task.probe_level,
                "scheduling_type": task.scheduling_type,
                "status": task.status,
                "progress": task.progress,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "last_probe_time": task.last_probe_time.isoformat() if task.last_probe_time else None,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except Exception as e:
        logger.error(f"获取探查任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取探查任务列表失败: {str(e)}"
        )


@router.get("/{task_id}", response_model=ResponseModel)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取任务详情"""
    try:
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == task.database_config_id).first()
        
        result = {
            "id": task.id,
            "task_name": task.task_name,
            "database_config_id": task.database_config_id,
            "database_config_name": db_config.name if db_config else "",
            "db_type": db_config.db_type if db_config else "",
            "probe_mode": task.probe_mode,
            "probe_level": task.probe_level,
            "scheduling_type": task.scheduling_type,
            "status": task.status,
            "progress": task.progress,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None,
            "last_probe_time": task.last_probe_time.isoformat() if task.last_probe_time else None,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建探查任务"""
    try:
        # 验证数据源配置
        db_config_id = task_data.get("database_config_id")
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == db_config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据源配置不存在")
        
        # 创建任务
        task = ProbeTask(
            user_id=current_user.id,
            database_config_id=db_config_id,
            task_name=task_data.get("task_name", f"{db_config.name}_探查"),
            probe_mode=task_data.get("probe_mode", "basic"),
            probe_level=task_data.get("probe_level", "database"),
            scheduling_type=task_data.get("scheduling_type", "manual"),
            status="pending"
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={"id": task.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建探查任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建探查任务失败: {str(e)}"
        )


@router.put("/{task_id}", response_model=ResponseModel)
async def update_task(
    task_id: int,
    task_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新任务配置"""
    try:
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 只能更新pending状态的任务
        if task.status != "pending":
            raise HTTPException(status_code=400, detail="只能更新待执行状态的任务")
        
        # 更新字段
        if "task_name" in task_data:
            task.task_name = task_data["task_name"]
        if "probe_mode" in task_data:
            task.probe_mode = task_data["probe_mode"]
        if "probe_level" in task_data:
            task.probe_level = task_data["probe_level"]
        if "scheduling_type" in task_data:
            task.scheduling_type = task_data["scheduling_type"]
        
        db.commit()
        db.refresh(task)
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={"id": task.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新任务配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务配置失败: {str(e)}"
        )


@router.delete("/{task_id}", response_model=ResponseModel)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除任务"""
    try:
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 运行中的任务不能删除
        if task.status == "running":
            raise HTTPException(status_code=400, detail="运行中的任务不能删除，请先停止")
        
        db.delete(task)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除任务失败: {str(e)}"
        )


@router.post("/{task_id}/start", response_model=ResponseModel)
async def start_task(
    task_id: int,
    task_data: Optional[Dict[str, Any]] = Body(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """启动任务"""
    try:
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status == "running":
            raise HTTPException(status_code=400, detail="任务已在运行中")
        
        # 如果任务已完成，重置状态以允许重新启动
        if task.status == "completed":
            task.status = "pending"
            task.progress = 0
            task.start_time = None
            task.end_time = None
            task.error_message = None
        
        # 如果提供了探查方式和级别，更新任务配置
        if task_data:
            if "probe_mode" in task_data:
                task.probe_mode = task_data["probe_mode"]
            if "probe_level" in task_data:
                task.probe_level = task_data["probe_level"]
            if "scheduling_type" in task_data:
                task.scheduling_type = task_data["scheduling_type"]
        
        # 提交状态更新
        db.commit()
        
        # 在后台线程中执行任务
        # 注意：需要创建新的数据库会话，因为当前会话在线程中可能不安全
        from app.core.database import LocalSessionLocal
        thread = threading.Thread(
            target=_execute_task_async,
            args=(task_id, LocalSessionLocal()),
            daemon=True
        )
        thread.start()
        
        return ResponseModel(
            success=True,
            message="任务已启动"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务失败: {str(e)}"
        )


@router.post("/{task_id}/stop", response_model=ResponseModel)
async def stop_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """停止任务"""
    try:
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status != "running":
            raise HTTPException(status_code=400, detail="任务未在运行中")
        
        executor = ProbeExecutor(db)
        executor.stop_task(task_id)
        
        return ResponseModel(
            success=True,
            message="任务已停止"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止任务失败: {str(e)}"
        )


@router.get("/by-database-config/{database_config_id}", response_model=ResponseModel)
async def get_task_by_database_config(
    database_config_id: int,
    probe_mode: Optional[str] = Query(None, description="探查方式"),
    probe_level: Optional[str] = Query(None, description="探查级别"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """根据数据源配置ID获取或创建探查任务"""
    try:
        # 验证数据源配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == database_config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据源配置不存在")
        
        # 如果指定了探查方式和级别，查找对应的任务
        if probe_mode and probe_level:
            task = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == database_config_id,
                ProbeTask.user_id == current_user.id,
                ProbeTask.probe_mode == probe_mode,
                ProbeTask.probe_level == probe_level
            ).first()
        else:
            # 否则优先查找有表级结果的任务，如果没有则查找有库级结果的任务，最后才查找最新任务
            from app.models import ProbeTableResult, ProbeDatabaseResult
            
            # 先查找有表级结果的任务（使用EXISTS子查询，性能更好）
            task_with_table_result = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == database_config_id,
                ProbeTask.user_id == current_user.id,
                exists().where(ProbeTableResult.task_id == ProbeTask.id)
            ).order_by(ProbeTask.created_at.desc()).first()
            
            if task_with_table_result:
                task = task_with_table_result
            else:
                # 如果没有表级结果，查找有库级结果的任务（使用EXISTS子查询）
                task_with_db_result = db.query(ProbeTask).filter(
                    ProbeTask.database_config_id == database_config_id,
                    ProbeTask.user_id == current_user.id,
                    exists().where(ProbeDatabaseResult.task_id == ProbeTask.id)
                ).order_by(ProbeTask.created_at.desc()).first()
                
                if task_with_db_result:
                    task = task_with_db_result
                else:
                    # 最后查找最新的任务
                    task = db.query(ProbeTask).filter(
                        ProbeTask.database_config_id == database_config_id,
                        ProbeTask.user_id == current_user.id
                    ).order_by(ProbeTask.created_at.desc()).first()
        
        # 如果没有任务，创建一个默认任务
        if not task:
            task = ProbeTask(
                user_id=current_user.id,
                database_config_id=database_config_id,
                task_name=f"{db_config.name}_{probe_mode or 'basic'}_{probe_level or 'database'}",
                probe_mode=probe_mode or "basic",
                probe_level=probe_level or "database",
                scheduling_type="manual",
                status="pending"
            )
            db.add(task)
            db.commit()
            db.refresh(task)
        
        # 检查是否有探查结果
        from app.models import ProbeDatabaseResult, ProbeTableResult
        has_database_result = db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task.id
        ).first() is not None
        has_table_result = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task.id
        ).first() is not None
        has_results = has_database_result or has_table_result
        
        result = {
            "id": task.id,
            "task_name": task.task_name,
            "database_config_id": task.database_config_id,
            "database_config_name": db_config.name,
            "db_type": db_config.db_type,
            "probe_mode": task.probe_mode,
            "probe_level": task.probe_level,
            "scheduling_type": task.scheduling_type,
            "status": task.status,
            "progress": task.progress,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None,
            "last_probe_time": task.last_probe_time.isoformat() if task.last_probe_time else None,
            "error_message": task.error_message,
            "has_results": has_results,  # 是否有探查结果
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取或创建探查任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取或创建探查任务失败: {str(e)}"
        )


@router.post("/batch-start", response_model=ResponseModel)
async def batch_start_tasks(
    request_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """批量启动任务"""
    try:
        task_ids = request_data.get("task_ids", [])
        probe_mode = request_data.get("probe_mode")
        scheduling_type = request_data.get("scheduling_type")
        
        if not task_ids:
            raise HTTPException(status_code=400, detail="任务ID列表不能为空")
        
        tasks = db.query(ProbeTask).filter(
            ProbeTask.id.in_(task_ids),
            ProbeTask.user_id == current_user.id
        ).all()
        
        if len(tasks) != len(task_ids):
            raise HTTPException(status_code=404, detail="部分任务不存在")
        
        started_count = 0
        for task in tasks:
            if task.status == "pending" or task.status == "stopped" or task.status == "failed":
                # 如果提供了探查方式和调度类型，更新任务配置
                if probe_mode:
                    task.probe_mode = probe_mode
                if scheduling_type:
                    task.scheduling_type = scheduling_type
                
                # 在后台线程中执行任务
                from app.core.database import LocalSessionLocal
                thread = threading.Thread(
                    target=_execute_task_async,
                    args=(task.id, LocalSessionLocal()),
                    daemon=True
                )
                thread.start()
                started_count += 1
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message=f"已启动 {started_count} 个任务",
            data={"started_count": started_count}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量启动任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量启动任务失败: {str(e)}"
        )

