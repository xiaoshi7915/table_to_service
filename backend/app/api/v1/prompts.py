"""
自定义提示词路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_local_db
from app.models import User, CustomPrompt
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from loguru import logger


router = APIRouter(prefix="/api/v1/prompts", tags=["自定义提示词"])


# ==================== 请求/响应模型 ====================

class CustomPromptCreate(BaseModel):
    """创建提示词请求模型"""
    name: str = Field(..., description="提示词名称")
    prompt_type: str = Field(..., description="类型（sql_generation, data_analysis等）")
    content: str = Field(..., description="提示词内容")
    priority: int = Field(0, description="优先级（数字越大优先级越高）")
    is_active: bool = Field(True, description="是否启用")


class CustomPromptUpdate(BaseModel):
    """更新提示词请求模型"""
    name: Optional[str] = None
    prompt_type: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


# ==================== API路由 ====================

@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_prompts(
    prompt_type: Optional[str] = Query(None, description="筛选提示词类型"),
    is_active: Optional[bool] = Query(None, description="筛选是否启用"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称或内容）"),
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取提示词列表"""
    try:
        query = db.query(CustomPrompt)
        
        # 类型筛选
        if prompt_type:
            query = query.filter(CustomPrompt.prompt_type == prompt_type)
        
        # 启用状态筛选
        if is_active is not None:
            query = query.filter(CustomPrompt.is_active == is_active)
        
        # 关键词搜索
        if keyword:
            query = query.filter(
                (CustomPrompt.name.like(f"%{keyword}%")) |
                (CustomPrompt.content.like(f"%{keyword}%"))
            )
        
        # 获取总数
        total = query.count()
        
        # 分页并排序（优先级降序，创建时间降序）
        offset = (page - 1) * page_size
        prompts = query.order_by(
            CustomPrompt.priority.desc(),
            CustomPrompt.created_at.desc()
        ).offset(offset).limit(page_size).all()
        
        result = []
        for prompt in prompts:
            result.append({
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "content": prompt.content,
                "priority": prompt.priority,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by,
                "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
                "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
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
        logger.error(f"获取提示词列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提示词列表失败: {str(e)}"
        )


@router.get("/{prompt_id}", response_model=ResponseModel)
async def get_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取提示词详情"""
    try:
        prompt = db.query(CustomPrompt).filter(CustomPrompt.id == prompt_id).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提示词不存在"
            )
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": prompt.id,
                "name": prompt.name,
                "prompt_type": prompt.prompt_type,
                "content": prompt.content,
                "priority": prompt.priority,
                "is_active": prompt.is_active,
                "created_by": prompt.created_by,
                "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
                "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提示词详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel)
@router.post("/", response_model=ResponseModel)
async def create_prompt(
    prompt_data: CustomPromptCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建提示词"""
    try:
        # 创建提示词
        prompt = CustomPrompt(
            name=prompt_data.name,
            prompt_type=prompt_data.prompt_type,
            content=prompt_data.content,
            priority=prompt_data.priority,
            is_active=prompt_data.is_active,
            created_by=current_user.id
        )
        
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        
        logger.info(f"用户 {current_user.username} 创建提示词: {prompt_data.name}")
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": prompt.id,
                "name": prompt.name
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"创建提示词失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建提示词失败: {str(e)}"
        )


@router.put("/{prompt_id}", response_model=ResponseModel)
async def update_prompt(
    prompt_id: int,
    prompt_data: CustomPromptUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新提示词"""
    try:
        prompt = db.query(CustomPrompt).filter(CustomPrompt.id == prompt_id).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提示词不存在"
            )
        
        # 更新字段
        update_data = {}
        if prompt_data.name is not None:
            update_data["name"] = prompt_data.name
        if prompt_data.prompt_type is not None:
            update_data["prompt_type"] = prompt_data.prompt_type
        if prompt_data.content is not None:
            update_data["content"] = prompt_data.content
        if prompt_data.priority is not None:
            update_data["priority"] = prompt_data.priority
        if prompt_data.is_active is not None:
            update_data["is_active"] = prompt_data.is_active
        
        # 执行更新
        db.query(CustomPrompt).filter(CustomPrompt.id == prompt_id).update(update_data)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 更新提示词: {prompt_id}")
        
        return ResponseModel(
            success=True,
            message="更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新提示词失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新提示词失败: {str(e)}"
        )


@router.delete("/{prompt_id}", response_model=ResponseModel)
async def delete_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除提示词"""
    try:
        prompt = db.query(CustomPrompt).filter(CustomPrompt.id == prompt_id).first()
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提示词不存在"
            )
        
        db.delete(prompt)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除提示词: {prompt.name}")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除提示词失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除提示词失败: {str(e)}"
        )


@router.get("/types/list", response_model=ResponseModel)
async def list_prompt_types(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有提示词类型列表"""
    try:
        # 查询所有不重复的类型
        types = db.query(CustomPrompt.prompt_type).distinct().all()
        
        type_list = [t[0] for t in types if t[0]]
        
        # 预定义的类型说明
        type_info = {
            "sql_generation": "SQL生成",
            "data_analysis": "数据分析",
            "chart_recommendation": "图表推荐",
            "question_understanding": "问题理解"
        }
        
        result = []
        for t in sorted(type_list):
            result.append({
                "type": t,
                "name": type_info.get(t, t)
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except Exception as e:
        logger.error(f"获取提示词类型列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提示词类型列表失败: {str(e)}"
        )


