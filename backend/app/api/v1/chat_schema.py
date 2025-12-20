"""
数据源Schema API
提供数据源表信息、关联关系、表结构、样例数据等接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_local_db
from app.core.security import get_current_active_user
from app.models import User, DatabaseConfig
from app.schemas import ResponseModel
from app.core.rag_langchain.schema_service import SchemaService

router = APIRouter(prefix="/api/v1/chat", tags=["对话Schema"])


@router.get("/datasources/{datasource_id}/tables", response_model=ResponseModel)
async def get_tables(
    datasource_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据源的表列表（优化版：只获取表名，不获取详细结构）"""
    try:
        # 验证数据源
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == datasource_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 直接获取表名列表，不获取详细结构（提升性能）
        from app.core.db_factory import DatabaseConnectionFactory
        from sqlalchemy import inspect, text
        
        db_type = db_config.db_type or "mysql"
        engine = DatabaseConnectionFactory.create_engine(db_config)
        
        try:
            inspector = inspect(engine)
            
            # 根据数据库类型获取表名列表
            if db_type == "sqlite":
                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    ))
                    table_names = [row[0] for row in result]
            elif db_type == "postgresql":
                table_names = inspector.get_table_names(schema='public')
            else:
                # MySQL、SQL Server、Oracle等
                table_names = inspector.get_table_names()
            
            # 只返回表名列表（简单格式，提升性能）
            tables = [{"name": name} for name in sorted(table_names)]
            
            engine.dispose()
            
            logger.info(f"获取数据源 {datasource_id} 的表列表，共 {len(tables)} 个表")
            
            return ResponseModel(
                success=True,
                message="获取成功",
                data=tables
            )
        except Exception as e:
            engine.dispose()
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表列表失败: {str(e)}")


@router.get("/datasources/{datasource_id}/schema", response_model=ResponseModel)
async def get_schema(
    datasource_id: int,
    table_names: Optional[List[str]] = Query(None, description="表名列表，多个用逗号分隔"),
    include_sample_data: bool = Query(True, description="是否包含样例数据"),
    sample_rows: int = Query(5, ge=1, le=20, description="样例数据行数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据源的Schema信息（表结构、关联关系、样例数据）"""
    try:
        # 验证数据源
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == datasource_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 解析表名列表
        selected_tables = None
        if table_names:
            if isinstance(table_names, str):
                selected_tables = [t.strip() for t in table_names.split(",") if t.strip()]
            else:
                selected_tables = table_names
        
        # 获取Schema信息
        schema_service = SchemaService(db_config)
        schema_info = schema_service.get_table_schema(
            table_names=selected_tables,
            include_sample_data=include_sample_data,
            sample_rows=sample_rows
        )
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=schema_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Schema信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取Schema信息失败: {str(e)}")


@router.get("/datasources/{datasource_id}/tables/{table_name}/structure", response_model=ResponseModel)
async def get_table_structure(
    datasource_id: int,
    table_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取单个表的详细结构信息"""
    try:
        # 验证数据源
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == datasource_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 获取表结构
        schema_service = SchemaService(db_config)
        schema_info = schema_service.get_table_schema(
            table_names=[table_name],
            include_sample_data=True,
            sample_rows=5
        )
        
        table_info = None
        for table in schema_info.get("tables", []):
            if table["name"] == table_name:
                table_info = table
                break
        
        if not table_info:
            raise HTTPException(status_code=404, detail="表不存在")
        
        # 获取关联关系
        relationships = [
            rel for rel in schema_info.get("relationships", [])
            if rel["from_table"] == table_name or rel["to_table"] == table_name
        ]
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "table": table_info,
                "relationships": relationships
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表结构失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取表结构失败: {str(e)}")


