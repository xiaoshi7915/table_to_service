"""
探查结果导出API
支持导出Excel和CSV格式
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse, Response, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import io
import csv
import json
from datetime import datetime
from loguru import logger

from app.core.database import get_local_db
from app.models import User, ProbeTask, ProbeDatabaseResult, ProbeTableResult, ProbeColumnResult
from app.schemas import ResponseModel
from app.core.security import get_current_active_user

router = APIRouter(prefix="/api/v1/probe-results", tags=["探查结果导出"])


@router.get("/task/{task_id}/export")
async def export_results(
    task_id: int,
    format: str = Query("excel", description="导出格式：excel/csv/json"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """导出探查结果"""
    try:
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if format == "excel":
            return await _export_to_excel(task_id, task, db)
        elif format == "csv":
            return await _export_to_csv(task_id, task, db)
        elif format == "json":
            return await _export_to_json(task_id, task, db)
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出探查结果失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败: {str(e)}"
        )


async def _export_to_excel(task_id: int, task: ProbeTask, db: Session):
    """导出为Excel格式"""
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 库级结果 - 查找当前任务或同一数据库配置、同一探查模式的其他任务
            db_result = db.query(ProbeDatabaseResult).filter(
                ProbeDatabaseResult.task_id == task_id
            ).first()
            
            if not db_result:
                # 查找同一数据库配置、同一探查模式的其他已完成任务的库级结果
                other_tasks = db.query(ProbeTask).filter(
                    ProbeTask.database_config_id == task.database_config_id,
                    ProbeTask.probe_mode == task.probe_mode,
                    ProbeTask.status == "completed",
                    ProbeTask.id != task_id
                ).order_by(ProbeTask.created_at.desc()).all()
                
                for other_task in other_tasks:
                    db_result = db.query(ProbeDatabaseResult).filter(
                        ProbeDatabaseResult.task_id == other_task.id
                    ).first()
                    if db_result:
                        break
            
            if db_result:
                db_data = {
                    "数据库名": [db_result.database_name],
                    "数据库类型": [db_result.db_type],
                    "总大小(MB)": [db_result.total_size_mb or ""],
                    "表数量": [db_result.table_count],
                    "视图数量": [db_result.view_count],
                    "函数数量": [db_result.function_count],
                    "存储过程数量": [db_result.procedure_count],
                    "触发器数量": [db_result.trigger_count],
                }
                pd.DataFrame(db_data).to_excel(writer, sheet_name="库级结果", index=False)
            
            # 表级结果
            table_results = db.query(ProbeTableResult).filter(
                ProbeTableResult.task_id == task_id
            ).all()
            
            if table_results:
                table_data = []
                for tr in table_results:
                    table_data.append({
                        "表名": tr.table_name,
                        "行数": tr.row_count or 0,
                        "表大小(MB)": tr.table_size_mb or "",
                        "索引大小(MB)": tr.index_size_mb or "",
                        "字段数": tr.column_count,
                        "主键": str(tr.primary_key) if tr.primary_key else "",
                        "是否冷表": "是" if tr.is_cold_table else "否",
                        "是否热表": "是" if tr.is_hot_table else "否",
                    })
                pd.DataFrame(table_data).to_excel(writer, sheet_name="表级结果", index=False)
            
            # 列级结果 - 查找当前任务或同一数据库配置、同一探查模式的其他任务
            column_results = db.query(ProbeColumnResult).filter(
                ProbeColumnResult.task_id == task_id
            ).limit(1000).all()  # 限制导出数量
            
            if not column_results:
                # 查找同一数据库配置、同一探查模式的其他已完成任务的列级结果
                other_tasks = db.query(ProbeTask).filter(
                    ProbeTask.database_config_id == task.database_config_id,
                    ProbeTask.probe_mode == task.probe_mode,
                    ProbeTask.status == "completed",
                    ProbeTask.id != task_id
                ).order_by(ProbeTask.created_at.desc()).all()
                
                for other_task in other_tasks:
                    column_results = db.query(ProbeColumnResult).filter(
                        ProbeColumnResult.task_id == other_task.id
                    ).limit(1000).all()
                    if column_results:
                        break
            
            if column_results:
                column_data = []
                for cr in column_results:
                    column_data.append({
                        "表名": cr.table_name,
                        "字段名": cr.column_name,
                        "数据类型": cr.data_type,
                        "是否可空": "是" if cr.nullable else "否",
                        "非空率": cr.non_null_rate or "",
                        "唯一值个数": cr.distinct_count or 0,
                        "重复率": cr.duplicate_rate or "",
                        "最大值": cr.max_value or "",
                        "最小值": cr.min_value or "",
                        "注释": cr.comment or "",
                    })
                pd.DataFrame(column_data).to_excel(writer, sheet_name="列级结果", index=False)
        
        output.seek(0)
        
        filename = f"探查结果_{task.task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    
    except ImportError:
        raise HTTPException(status_code=500, detail="Excel导出功能需要安装pandas和openpyxl库")
    except Exception as e:
        logger.error(f"Excel导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel导出失败: {str(e)}")


async def _export_to_csv(task_id: int, task: ProbeTask, db: Session):
    """导出为CSV格式（多个文件打包）"""
    try:
        import zipfile
        
        output = io.BytesIO()
        zip_file = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
        
        # 库级结果 - 查找当前任务或同一数据库配置、同一探查模式的其他任务
        db_result = db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task_id
        ).first()
        
        if not db_result:
            # 查找同一数据库配置、同一探查模式的其他已完成任务的库级结果
            other_tasks = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed",
                ProbeTask.id != task_id
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                db_result = db.query(ProbeDatabaseResult).filter(
                    ProbeDatabaseResult.task_id == other_task.id
                ).first()
                if db_result:
                    break
        
        if db_result:
            csv_data = io.StringIO()
            writer = csv.writer(csv_data)
            writer.writerow(["数据库名", "数据库类型", "总大小(MB)", "表数量", "视图数量", "函数数量", "存储过程数量", "触发器数量"])
            writer.writerow([
                db_result.database_name,
                db_result.db_type,
                db_result.total_size_mb or "",
                db_result.table_count,
                db_result.view_count,
                db_result.function_count,
                db_result.procedure_count,
                db_result.trigger_count,
            ])
            zip_file.writestr("库级结果.csv", csv_data.getvalue().encode('utf-8-sig'))
        
        # 表级结果
        table_results = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id
        ).all()
        
        if table_results:
            csv_data = io.StringIO()
            writer = csv.writer(csv_data)
            writer.writerow(["表名", "行数", "表大小(MB)", "索引大小(MB)", "字段数", "主键", "是否冷表", "是否热表"])
            for tr in table_results:
                writer.writerow([
                    tr.table_name,
                    tr.row_count or 0,
                    tr.table_size_mb or "",
                    tr.index_size_mb or "",
                    tr.column_count,
                    str(tr.primary_key) if tr.primary_key else "",
                    "是" if tr.is_cold_table else "否",
                    "是" if tr.is_hot_table else "否",
                ])
            zip_file.writestr("表级结果.csv", csv_data.getvalue().encode('utf-8-sig'))
        
        # 列级结果 - 查找当前任务或同一数据库配置、同一探查模式的其他任务
        column_results = db.query(ProbeColumnResult).filter(
            ProbeColumnResult.task_id == task_id
        ).limit(1000).all()
        
        if not column_results:
            # 查找同一数据库配置、同一探查模式的其他已完成任务的列级结果
            other_tasks = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed",
                ProbeTask.id != task_id
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                column_results = db.query(ProbeColumnResult).filter(
                    ProbeColumnResult.task_id == other_task.id
                ).limit(1000).all()
                if column_results:
                    break
        
        if column_results:
            csv_data = io.StringIO()
            writer = csv.writer(csv_data)
            writer.writerow(["表名", "字段名", "数据类型", "是否可空", "非空率", "唯一值个数", "重复率", "最大值", "最小值", "注释"])
            for cr in column_results:
                writer.writerow([
                    cr.table_name,
                    cr.column_name,
                    cr.data_type,
                    "是" if cr.nullable else "否",
                    cr.non_null_rate or "",
                    cr.distinct_count or 0,
                    cr.duplicate_rate or "",
                    cr.max_value or "",
                    cr.min_value or "",
                    cr.comment or "",
                ])
            zip_file.writestr("列级结果.csv", csv_data.getvalue().encode('utf-8-sig'))
        
        zip_file.close()
        output.seek(0)
        
        filename = f"探查结果_{task.task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"CSV导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CSV导出失败: {str(e)}")


async def _export_to_json(task_id: int, task: ProbeTask, db: Session):
    """导出为JSON格式"""
    try:
        # 获取所有探查结果 - 查找当前任务或同一数据库配置、同一探查模式的其他任务
        db_result = db.query(ProbeDatabaseResult).filter(
            ProbeDatabaseResult.task_id == task_id
        ).first()
        
        if not db_result:
            # 查找同一数据库配置、同一探查模式的其他已完成任务的库级结果
            other_tasks = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed",
                ProbeTask.id != task_id
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                db_result = db.query(ProbeDatabaseResult).filter(
                    ProbeDatabaseResult.task_id == other_task.id
                ).first()
                if db_result:
                    break
        
        table_results = db.query(ProbeTableResult).filter(
            ProbeTableResult.task_id == task_id
        ).all()
        
        column_results = db.query(ProbeColumnResult).filter(
            ProbeColumnResult.task_id == task_id
        ).all()
        
        if not column_results:
            # 查找同一数据库配置、同一探查模式的其他已完成任务的列级结果
            other_tasks = db.query(ProbeTask).filter(
                ProbeTask.database_config_id == task.database_config_id,
                ProbeTask.probe_mode == task.probe_mode,
                ProbeTask.status == "completed",
                ProbeTask.id != task_id
            ).order_by(ProbeTask.created_at.desc()).all()
            
            for other_task in other_tasks:
                column_results = db.query(ProbeColumnResult).filter(
                    ProbeColumnResult.task_id == other_task.id
                ).all()
                if column_results:
                    break
        
        # 构建JSON数据
        export_data = {
            "task_id": task_id,
            "task_name": task.task_name,
            "probe_mode": task.probe_mode,
            "probe_level": task.probe_level,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "last_probe_time": task.last_probe_time.isoformat() if task.last_probe_time else None,
            "database_result": None,
            "table_results": [],
            "column_results": []
        }
        
        # 库级结果
        if db_result:
            export_data["database_result"] = {
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
            }
        
        # 表级结果
        for tr in table_results:
            export_data["table_results"].append({
                "table_name": tr.table_name,
                "schema_name": tr.schema_name,
                "row_count": tr.row_count,
                "table_size_mb": tr.table_size_mb,
                "index_size_mb": tr.index_size_mb,
                "column_count": tr.column_count,
                "primary_key": tr.primary_key,
                "indexes": tr.indexes,
                "foreign_keys": tr.foreign_keys,
                "constraints": tr.constraints,
                "is_cold_table": tr.is_cold_table,
                "is_hot_table": tr.is_hot_table,
            })
        
        # 列级结果
        for cr in column_results:
            export_data["column_results"].append({
                "table_name": cr.table_name,
                "column_name": cr.column_name,
                "data_type": cr.data_type,
                "nullable": cr.nullable,
                "non_null_rate": cr.non_null_rate,
                "distinct_count": cr.distinct_count,
                "duplicate_rate": cr.duplicate_rate,
                "max_value": cr.max_value,
                "min_value": cr.min_value,
                "top_values": cr.top_values,
                "data_quality_issues": cr.data_quality_issues,
                "sensitive_info": cr.sensitive_info,
            })
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=probe_result_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    except Exception as e:
        logger.error(f"JSON导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"JSON导出失败: {str(e)}")


@router.post("/task/{task_id}/import-to-knowledge", response_model=ResponseModel)
async def import_to_knowledge(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """导入探查结果到知识库"""
    try:
        from app.core.probe.knowledge_importer import ProbeResultKnowledgeImporter
        
        # 验证任务权限
        task = db.query(ProbeTask).filter(
            ProbeTask.id == task_id,
            ProbeTask.user_id == current_user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 导入到知识库
        importer = ProbeResultKnowledgeImporter(db)
        result = importer.import_to_knowledge(task_id, current_user.id)
        
        return ResponseModel(
            success=True,
            message="导入成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入到知识库失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入到知识库失败: {str(e)}"
        )

