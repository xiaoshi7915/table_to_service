"""
SQL示例库路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_local_db
from app.models import User, SQLExample
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from loguru import logger


router = APIRouter(prefix="/api/v1/sql-examples", tags=["SQL示例配置"])


# ==================== 请求/响应模型 ====================

class SQLExampleCreate(BaseModel):
    """创建SQL示例请求模型"""
    title: str = Field(..., description="示例标题")
    question: str = Field(..., description="对应的问题（自然语言）")
    sql_statement: str = Field(..., description="SQL语句")
    db_type: str = Field(..., description="数据库类型")
    table_name: Optional[str] = Field(None, description="涉及的表名")
    description: Optional[str] = Field(None, description="示例说明")
    chart_type: Optional[str] = Field(None, description="推荐图表类型")


class SQLExampleUpdate(BaseModel):
    """更新SQL示例请求模型"""
    title: Optional[str] = None
    question: Optional[str] = None
    sql_statement: Optional[str] = None
    db_type: Optional[str] = None
    table_name: Optional[str] = None
    description: Optional[str] = None
    chart_type: Optional[str] = None


# ==================== API路由 ====================

@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_sql_examples(
    db_type: Optional[str] = Query(None, description="筛选数据库类型"),
    table_name: Optional[str] = Query(None, description="筛选表名"),
    keyword: Optional[str] = Query(None, description="搜索关键词（标题或问题）"),
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取SQL示例列表"""
    try:
        query = db.query(SQLExample)
        
        # 数据库类型筛选
        if db_type:
            query = query.filter(SQLExample.db_type == db_type)
        
        # 表名筛选
        if table_name:
            query = query.filter(SQLExample.table_name == table_name)
        
        # 关键词搜索
        if keyword:
            query = query.filter(
                (SQLExample.title.like(f"%{keyword}%")) |
                (SQLExample.question.like(f"%{keyword}%")) |
                (SQLExample.description.like(f"%{keyword}%"))
            )
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        examples = query.order_by(SQLExample.created_at.desc()).offset(offset).limit(page_size).all()
        
        result = []
        for example in examples:
            result.append({
                "id": example.id,
                "title": example.title,
                "question": example.question,
                "sql_statement": example.sql_statement,
                "db_type": example.db_type,
                "table_name": example.table_name,
                "description": example.description,
                "chart_type": example.chart_type,
                "created_by": example.created_by,
                "created_at": example.created_at.isoformat() if example.created_at else None,
                "updated_at": example.updated_at.isoformat() if example.updated_at else None
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
        logger.error(f"获取SQL示例列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SQL示例列表失败: {str(e)}"
        )


@router.get("/{example_id}", response_model=ResponseModel)
async def get_sql_example(
    example_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取SQL示例详情"""
    try:
        example = db.query(SQLExample).filter(SQLExample.id == example_id).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SQL示例不存在"
            )
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": example.id,
                "title": example.title,
                "question": example.question,
                "sql_statement": example.sql_statement,
                "db_type": example.db_type,
                "table_name": example.table_name,
                "description": example.description,
                "chart_type": example.chart_type,
                "created_by": example.created_by,
                "created_at": example.created_at.isoformat() if example.created_at else None,
                "updated_at": example.updated_at.isoformat() if example.updated_at else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SQL示例详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SQL示例详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel)
@router.post("/", response_model=ResponseModel)
async def create_sql_example(
    example_data: SQLExampleCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建SQL示例"""
    try:
        # 验证数据库类型
        supported_db_types = ["mysql", "postgresql", "sqlite", "sqlserver", "oracle"]
        if example_data.db_type.lower() not in supported_db_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的数据库类型: {example_data.db_type}，支持的类型: {supported_db_types}"
            )
        
        # 创建SQL示例
        sql_example = SQLExample(
            title=example_data.title,
            question=example_data.question,
            sql_statement=example_data.sql_statement,
            db_type=example_data.db_type.lower(),
            table_name=example_data.table_name,
            description=example_data.description,
            chart_type=example_data.chart_type,
            created_by=current_user.id
        )
        
        db.add(sql_example)
        db.commit()
        db.refresh(sql_example)
        
        logger.info(f"用户 {current_user.username} 创建SQL示例: {example_data.title}")
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": sql_example.id,
                "title": sql_example.title
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建SQL示例失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建SQL示例失败: {str(e)}"
        )


@router.put("/{example_id}", response_model=ResponseModel)
async def update_sql_example(
    example_id: int,
    example_data: SQLExampleUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新SQL示例"""
    try:
        example = db.query(SQLExample).filter(SQLExample.id == example_id).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SQL示例不存在"
            )
        
        # 更新字段
        update_data = {}
        if example_data.title is not None:
            update_data["title"] = example_data.title
        if example_data.question is not None:
            update_data["question"] = example_data.question
        if example_data.sql_statement is not None:
            update_data["sql_statement"] = example_data.sql_statement
        if example_data.db_type is not None:
            update_data["db_type"] = example_data.db_type.lower()
        if example_data.table_name is not None:
            update_data["table_name"] = example_data.table_name
        if example_data.description is not None:
            update_data["description"] = example_data.description
        if example_data.chart_type is not None:
            update_data["chart_type"] = example_data.chart_type
        
        # 执行更新
        db.query(SQLExample).filter(SQLExample.id == example_id).update(update_data)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 更新SQL示例: {example_id}")
        
        return ResponseModel(
            success=True,
            message="更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新SQL示例失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新SQL示例失败: {str(e)}"
        )


@router.delete("/{example_id}", response_model=ResponseModel)
async def delete_sql_example(
    example_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除SQL示例"""
    try:
        example = db.query(SQLExample).filter(SQLExample.id == example_id).first()
        
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SQL示例不存在"
            )
        
        db.delete(example)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除SQL示例: {example.title}")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除SQL示例失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除SQL示例失败: {str(e)}"
        )


