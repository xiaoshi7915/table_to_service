"""
探查结果查询API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from app.core.database import get_local_db
from app.models import User, ProbeTask, ProbeDatabaseResult, ProbeTableResult, ProbeColumnResult
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from loguru import logger


router = APIRouter(prefix="/api/v1/probe-results", tags=["探查结果"])


@router.get("/task/{task_id}/database", response_model=ResponseModel)
async def get_database_result(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取库级探查结果"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取库级结果
        db_result = db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task_id
        ).first()
        
        if not db_result:
            return ResponseModel(
                success=True,
                message="暂无库级探查结果",
                data=None
            )
        
        result = {
            "id": db_result.id,
            "task_id": db_result.task_id,
            "database_name": db_result.database_name,
            "db_type": db_result.db_type,
            "total_size_mb": db_result.total_size_mb,
            "growth_rate": db_result.growth_rate,
            "table_count": db_result.table_count,
            "view_count": db_result.view_count,
            "function_count": db_result.function_count,
            "procedure_count": db_result.procedure_count,
            "trigger_count": db_result.trigger_count,
            "event_count": db_result.event_count,
            "sequence_count": db_result.sequence_count,
            "top_n_tables": db_result.top_n_tables,
            "cold_tables": db_result.cold_tables,
            "hot_tables": db_result.hot_tables,
            "high_risk_accounts": db_result.high_risk_accounts,
            "permission_summary": db_result.permission_summary,
            "created_at": db_result.created_at.isoformat() if db_result.created_at else None,
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取库级探查结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取库级探查结果失败: {str(e)}"
        )


@router.get("/task/{task_id}/tables", response_model=ResponseModel)
async def get_table_results(
    task_id: int,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索表名"),
    is_hidden: Optional[bool] = Query(None, description="是否屏蔽"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取表级探查结果列表"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 查询表结果
        query = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id
        )
        
        # 搜索
        if search:
            query = query.filter(ProbeTableResult.table_name.like(f"%{search}%"))
        
        # 筛选屏蔽状态
        if is_hidden is not None:
            query = query.filter(ProbeTableResult.is_hidden == is_hidden)
        
        # 排序
        query = query.order_by(ProbeTableResult.table_name)
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        table_results = query.offset(offset).limit(page_size).all()
        
        result = []
        for tr in table_results:
            result.append({
                "id": tr.id,
                "task_id": tr.task_id,
                "database_name": tr.database_name,
                "table_name": tr.table_name,
                "schema_name": tr.schema_name,
                "row_count": tr.row_count,
                "table_size_mb": tr.table_size_mb,
                "index_size_mb": tr.index_size_mb,
                "avg_row_length": tr.avg_row_length,
                "fragmentation_rate": tr.fragmentation_rate,
                "column_count": tr.column_count,
                "comment": tr.comment,
                "primary_key": tr.primary_key,
                "indexes": tr.indexes,
                "foreign_keys": tr.foreign_keys,
                "constraints": tr.constraints,
                "partition_info": tr.partition_info,
                "is_cold_table": tr.is_cold_table,
                "is_hot_table": tr.is_hot_table,
                "is_hidden": tr.is_hidden,
                "created_at": tr.created_at.isoformat() if tr.created_at else None,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表级探查结果列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表级探查结果列表失败: {str(e)}"
        )


@router.get("/task/{task_id}/tables/{table_name}", response_model=ResponseModel)
async def get_table_result(
    task_id: int,
    table_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取指定表的探查结果"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取表结果
        table_result = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id,
            ProbeTableResult.table_name == table_name
        ).first()
        
        if not table_result:
            raise HTTPException(status_code=404, detail="表探查结果不存在")
        
        result = {
            "id": table_result.id,
            "task_id": table_result.task_id,
            "database_name": table_result.database_name,
            "table_name": table_result.table_name,
            "schema_name": table_result.schema_name,
            "row_count": table_result.row_count,
            "table_size_mb": table_result.table_size_mb,
            "index_size_mb": table_result.index_size_mb,
            "avg_row_length": table_result.avg_row_length,
            "fragmentation_rate": table_result.fragmentation_rate,
            "auto_increment_usage": table_result.auto_increment_usage,
            "column_count": table_result.column_count,
            "primary_key": table_result.primary_key,
            "indexes": table_result.indexes,
            "foreign_keys": table_result.foreign_keys,
            "constraints": table_result.constraints,
            "partition_info": table_result.partition_info,
            "is_cold_table": table_result.is_cold_table,
            "is_hot_table": table_result.is_hot_table,
            "last_access_time": table_result.last_access_time.isoformat() if table_result.last_access_time else None,
            "is_hidden": table_result.is_hidden,
            "created_at": table_result.created_at.isoformat() if table_result.created_at else None,
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表探查结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表探查结果失败: {str(e)}"
        )


@router.get("/task/{task_id}/tables/{table_name}/columns", response_model=ResponseModel)
async def get_column_results(
    task_id: int,
    table_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取指定表的列级探查结果"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取表结果ID（如果表结果不存在，仍然尝试获取列结果）
        table_result = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id,
            ProbeTableResult.table_name == table_name
        ).first()
        
        # 获取列结果（即使表结果不存在，也可能有列结果）
        column_results = db.query(ProbeColumnResult).filter(
            ProbeColumnResult.task_id == task_id,
            ProbeColumnResult.table_name == table_name
        ).order_by(ProbeColumnResult.column_name).all()
        
        # 如果没有列结果，尝试查找同一数据库配置的其他任务的列结果
        if not column_results:
            # 查找同一数据库配置、同一探查模式的其他已完成任务
            other_tasks = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed",
                ProbeTask.id != task_id
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                column_results = db.query(ProbeColumnResult).filter(
                    ProbeColumnResult.task_id == other_task.id,
                    ProbeColumnResult.table_name == table_name
                ).order_by(ProbeColumnResult.column_name).all()
                
                if column_results:
                    break
        
        if not table_result and not column_results:
            raise HTTPException(status_code=404, detail="表探查结果不存在")
        
        result = []
        seen_columns = set()  # 用于去重
        for cr in column_results:
            # 如果字段名已存在，跳过（去重）
            column_key = f"{cr.table_name}.{cr.column_name}"
            if column_key in seen_columns:
                continue
            seen_columns.add(column_key)
            
            result.append({
                "id": cr.id,
                "task_id": cr.task_id,
                "table_result_id": cr.table_result_id,
                "database_name": cr.database_name,
                "table_name": cr.table_name,
                "column_name": cr.column_name,
                "data_type": cr.data_type,
                "nullable": cr.nullable,
                "default_value": cr.default_value,
                "comment": cr.comment,
                "non_null_rate": cr.non_null_rate,
                "distinct_count": cr.distinct_count,
                "duplicate_rate": cr.duplicate_rate,
                "max_length": cr.max_length,
                "min_length": cr.min_length,
                "avg_length": cr.avg_length,
                "max_value": cr.max_value,
                "min_value": cr.min_value,
                "top_values": cr.top_values,
                "low_frequency_values": cr.low_frequency_values,
                "enum_values": cr.enum_values,
                "zero_count": cr.zero_count,
                "negative_count": cr.negative_count,
                "percentiles": cr.percentiles,
                "date_range": cr.date_range,
                "missing_rate": cr.missing_rate,
                "data_quality_issues": cr.data_quality_issues,
                "sensitive_info": cr.sensitive_info,
                "created_at": cr.created_at.isoformat() if cr.created_at else None,
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取列级探查结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取列级探查结果失败: {str(e)}"
        )


@router.get("/task/{task_id}/columns/{column_id}", response_model=ResponseModel)
async def get_column_result(
    task_id: int,
    column_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取指定列的详细探查结果"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取列结果
        column_result = db.query(ProbeColumnResult).filter(
            ProbeColumnResult.id == column_id,
            ProbeColumnResult.task_id == task_id
        ).first()
        
        if not column_result:
            raise HTTPException(status_code=404, detail="列探查结果不存在")
        
        result = {
            "id": column_result.id,
            "task_id": column_result.task_id,
            "table_result_id": column_result.table_result_id,
            "database_name": column_result.database_name,
            "table_name": column_result.table_name,
            "column_name": column_result.column_name,
            "data_type": column_result.data_type,
            "nullable": column_result.nullable,
            "default_value": column_result.default_value,
            "comment": column_result.comment,
            "non_null_rate": column_result.non_null_rate,
            "distinct_count": column_result.distinct_count,
            "duplicate_rate": column_result.duplicate_rate,
            "max_length": column_result.max_length,
            "min_length": column_result.min_length,
            "avg_length": column_result.avg_length,
            "max_value": column_result.max_value,
            "min_value": column_result.min_value,
            "top_values": column_result.top_values,
            "low_frequency_values": column_result.low_frequency_values,
            "enum_values": column_result.enum_values,
            "zero_count": column_result.zero_count,
            "negative_count": column_result.negative_count,
            "percentiles": column_result.percentiles,
            "date_range": column_result.date_range,
            "missing_rate": column_result.missing_rate,
            "data_quality_issues": column_result.data_quality_issues,
            "sensitive_info": column_result.sensitive_info,
            "created_at": column_result.created_at.isoformat() if column_result.created_at else None,
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取列探查结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取列探查结果失败: {str(e)}"
        )


@router.put("/task/{task_id}/tables/{table_name}/hide", response_model=ResponseModel)
async def hide_table(
    task_id: int,
    table_name: str,
    is_hidden: bool = Query(True, description="是否屏蔽"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """屏蔽/取消屏蔽表"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 更新表结果
        table_result = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id,
            ProbeTableResult.table_name == table_name
        ).first()
        
        if not table_result:
            raise HTTPException(status_code=404, detail="表探查结果不存在")
        
        table_result.is_hidden = is_hidden
        db.commit()
        
        return ResponseModel(
            success=True,
            message="操作成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"屏蔽/取消屏蔽表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"操作失败: {str(e)}"
        )

