"""
CocoIndex 管理路由
用于查看同步状态、索引统计等
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.core.database import get_local_db
from app.models import User, Document, DocumentChunk, DataSourceConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.cocoindex.sync.sync_service import sync_service
from app.core.cocoindex.config import cocoindex_config
from app.core.cocoindex.indexes.index_manager import IndexManager
from app.core.cocoindex.utils.embedding_helper import EmbeddingHelper
from app.core.cocoindex.utils.health_checker import HealthChecker


router = APIRouter(prefix="/api/v1/cocoindex", tags=["CocoIndex管理"])


# ==================== API路由 ====================

@router.get("/status", response_model=ResponseModel)
async def get_index_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取索引状态统计"""
    try:
        # 统计文档数量
        total_documents = db.query(Document).filter(Document.is_deleted == False).count()
        completed_documents = db.query(Document).filter(
            Document.is_deleted == False,
            Document.status == "completed"
        ).count()
        processing_documents = db.query(Document).filter(
            Document.is_deleted == False,
            Document.status == "processing"
        ).count()
        failed_documents = db.query(Document).filter(
            Document.is_deleted == False,
            Document.status == "failed"
        ).count()
        
        # 统计分块数量
        total_chunks = db.query(DocumentChunk).count()
        chunks_with_embedding = db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).count()
        
        # 统计数据源数量
        total_data_sources = db.query(DataSourceConfig).filter(
            DataSourceConfig.is_deleted == False
        ).count()
        enabled_data_sources = db.query(DataSourceConfig).filter(
            DataSourceConfig.is_deleted == False,
            DataSourceConfig.sync_enabled == True
        ).count()
        
        # 获取同步状态
        sync_status = sync_service.get_sync_status()
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "documents": {
                    "total": total_documents,
                    "completed": completed_documents,
                    "processing": processing_documents,
                    "failed": failed_documents
                },
                "chunks": {
                    "total": total_chunks,
                    "with_embedding": chunks_with_embedding,
                    "without_embedding": total_chunks - chunks_with_embedding
                },
                "data_sources": {
                    "total": total_data_sources,
                    "enabled": enabled_data_sources
                },
                "sync_status": sync_status,
                "collections": list(cocoindex_config.INDEX_COLLECTIONS.keys())
            }
        )
    except Exception as e:
        logger.error(f"获取索引状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取索引状态失败: {str(e)}"
        )


@router.get("/sync-status", response_model=ResponseModel)
async def get_all_sync_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有数据源的同步状态"""
    try:
        status_info = sync_service.get_sync_status()
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=status_info
        )
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步状态失败: {str(e)}"
        )


@router.get("/health", response_model=ResponseModel)
async def get_health_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取系统健康状态"""
    try:
        health_checker = HealthChecker(db_session=db)
        health_status = health_checker.check_all()
        
        return ResponseModel(
            success=True,
            message="健康检查完成",
            data=health_status
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/sync-all", response_model=ResponseModel)
async def sync_all_sources(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """同步所有启用的数据源"""
    try:
        # 获取所有启用的数据源
        data_sources = db.query(DataSourceConfig).filter(
            DataSourceConfig.is_deleted == False,
            DataSourceConfig.sync_enabled == True
        ).all()
        
        results = []
        for ds in data_sources:
            try:
                result = sync_service.start_sync(ds.source_type, ds.name)
                results.append({
                    "source_id": ds.id,
                    "source_name": ds.name,
                    "success": result.get("success", False),
                    "message": result.get("message", "")
                })
                
                # 更新最后同步时间
                if result.get("success"):
                    ds.last_sync_at = db.query(db.func.now()).scalar()
            except Exception as e:
                logger.error(f"同步数据源失败 {ds.name}: {e}")
                results.append({
                    "source_id": ds.id,
                    "source_name": ds.name,
                    "success": False,
                    "message": str(e)
                })
        
        db.commit()
        
        success_count = sum(1 for r in results if r["success"])
        
        return ResponseModel(
            success=True,
            message=f"同步完成：{success_count}/{len(results)} 个数据源同步成功",
            data={
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count,
                "results": results
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"同步所有数据源失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步所有数据源失败: {str(e)}"
        )


@router.post("/ensure-indexes", response_model=ResponseModel)
async def ensure_indexes(
    collection_name: Optional[str] = Query(None, description="集合名称（可选，不指定则创建所有集合的索引）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """确保索引已创建"""
    try:
        index_manager = IndexManager(db_session=db)
        
        if collection_name:
            # 创建指定集合的索引
            success = index_manager.ensure_indexes(collection_name)
            if success:
                return ResponseModel(
                    success=True,
                    message=f"索引创建成功: {collection_name}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="索引创建失败"
                )
        else:
            # 创建所有集合的索引
            results = {}
            for coll_name in cocoindex_config.INDEX_COLLECTIONS.values():
                success = index_manager.ensure_indexes(coll_name)
                results[coll_name] = "success" if success else "failed"
            
            success_count = sum(1 for v in results.values() if v == "success")
            
            return ResponseModel(
                success=True,
                message=f"索引创建完成：{success_count}/{len(results)} 个集合成功",
                data={"results": results}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建索引失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建索引失败: {str(e)}"
        )


@router.post("/ensure-embeddings", response_model=ResponseModel)
async def ensure_embeddings(
    document_id: Optional[int] = Query(None, description="文档ID（可选，不指定则处理所有文档）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """确保所有文档分块都有向量"""
    try:
        embedding_helper = EmbeddingHelper()
        
        if document_id:
            # 更新指定文档的向量
            updated = embedding_helper.update_document_chunk_embeddings(db, document_id=document_id)
            return ResponseModel(
                success=True,
                message=f"向量更新完成：{updated} 个分块",
                data={"updated": updated}
            )
        else:
            # 更新所有文档的向量
            stats = embedding_helper.ensure_all_embeddings(db)
            return ResponseModel(
                success=True,
                message=f"向量更新完成：{stats.get('updated', 0)} 个分块",
                data=stats
            )
    except Exception as e:
        logger.error(f"更新向量失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新向量失败: {str(e)}"
        )


@router.get("/scheduled-jobs", response_model=ResponseModel)
async def get_scheduled_jobs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有定时任务列表"""
    try:
        # 获取所有启用的数据源及其定时配置
        data_sources = db.query(DataSourceConfig).filter(
            DataSourceConfig.is_deleted == False
        ).all()
        
        jobs = []
        for ds in data_sources:
            job_info = {
                "id": ds.id,
                "name": ds.name,
                "source_type": ds.source_type,
                "sync_enabled": ds.sync_enabled,
                "sync_frequency": ds.sync_frequency,
                "last_sync_at": ds.last_sync_at.isoformat() if ds.last_sync_at else None,
                "next_run_time": None,
                "status": "enabled" if ds.sync_enabled and ds.sync_frequency else "disabled"
            }
            
            # 如果 APScheduler 可用，尝试获取实际的任务信息
            try:
                from app.core.cocoindex.sync.scheduler import sync_scheduler
                if sync_scheduler.running:
                    scheduled_jobs = sync_scheduler.get_scheduled_jobs()
                    job_id = f"{ds.source_type}:{ds.name}"
                    for job in scheduled_jobs.get("jobs", []):
                        if job["id"] == job_id:
                            job_info["next_run_time"] = job.get("next_run_time")
                            job_info["trigger"] = job.get("trigger")
                            break
            except Exception as e:
                logger.debug(f"获取任务详情失败: {e}")
            
            jobs.append(job_info)
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "jobs": jobs,
                "total": len(jobs),
                "enabled": sum(1 for j in jobs if j["status"] == "enabled"),
                "disabled": sum(1 for j in jobs if j["status"] == "disabled"),
                "scheduler_running": False  # 将在下面更新
            }
        )
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取定时任务列表失败: {str(e)}"
        )


@router.put("/scheduled-jobs/{job_id}", response_model=ResponseModel)
async def update_scheduled_job(
    job_id: int,
    sync_enabled: Optional[bool] = Query(None, description="是否启用同步"),
    sync_frequency: Optional[int] = Query(None, description="同步频率（秒）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新定时任务配置"""
    try:
        data_source = db.query(DataSourceConfig).filter(
            DataSourceConfig.id == job_id,
            DataSourceConfig.is_deleted == False
        ).first()
        
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 更新配置
        if sync_enabled is not None:
            data_source.sync_enabled = sync_enabled
        if sync_frequency is not None:
            data_source.sync_frequency = sync_frequency
        
        db.commit()
        db.refresh(data_source)
        
        # 如果调度器正在运行，更新任务
        try:
            from app.core.cocoindex.sync.scheduler import sync_scheduler
            if sync_scheduler.running:
                if data_source.sync_enabled and data_source.sync_frequency:
                    sync_scheduler.schedule_source_sync(
                        source_type=data_source.source_type,
                        source_name=data_source.name,
                        sync_frequency=data_source.sync_frequency
                    )
                else:
                    sync_scheduler.remove_source_sync(
                        source_type=data_source.source_type,
                        source_name=data_source.name
                    )
        except Exception as e:
            logger.warning(f"更新调度器任务失败: {e}")
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={
                "id": data_source.id,
                "name": data_source.name,
                "sync_enabled": data_source.sync_enabled,
                "sync_frequency": data_source.sync_frequency
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新定时任务配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新定时任务配置失败: {str(e)}"
        )
