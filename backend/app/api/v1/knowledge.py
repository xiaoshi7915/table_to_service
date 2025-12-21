"""
业务知识库路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_local_db
from app.models import User, BusinessKnowledge
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from loguru import logger
from sqlalchemy import or_


router = APIRouter(prefix="/api/v1/knowledge", tags=["业务知识库"])


# ==================== 请求/响应模型 ====================

class BusinessKnowledgeCreate(BaseModel):
    """创建知识条目请求模型"""
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[str] = Field(None, description="标签（逗号分隔）")


class BusinessKnowledgeUpdate(BaseModel):
    """更新知识条目请求模型"""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


# ==================== API路由 ====================

@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def search_knowledge(
    keyword: Optional[str] = Query(None, description="搜索关键词（标题或内容）"),
    category: Optional[str] = Query(None, description="筛选分类"),
    tag: Optional[str] = Query(None, description="筛选标签"),
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """搜索知识库"""
    try:
        query = db.query(BusinessKnowledge).filter(BusinessKnowledge.is_deleted == False)
        
        # 关键词搜索（标题或内容）
        if keyword:
            query = query.filter(
                or_(
                    BusinessKnowledge.title.like(f"%{keyword}%"),
                    BusinessKnowledge.content.like(f"%{keyword}%")
                )
            )
        
        # 分类筛选
        if category:
            query = query.filter(BusinessKnowledge.category == category)
        
        # 标签筛选
        if tag:
            query = query.filter(BusinessKnowledge.tags.like(f"%{tag}%"))
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        knowledge_list = query.order_by(BusinessKnowledge.created_at.desc()).offset(offset).limit(page_size).all()
        
        result = []
        for knowledge in knowledge_list:
            # 解析标签
            tags_list = []
            if knowledge.tags:
                tags_list = [t.strip() for t in knowledge.tags.split(",") if t.strip()]
            
            result.append({
                "id": knowledge.id,
                "title": knowledge.title,
                "content": knowledge.content,
                "category": knowledge.category,
                "tags": tags_list,
                "created_by": knowledge.created_by,
                "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None,
                "updated_at": knowledge.updated_at.isoformat() if knowledge.updated_at else None
            })
        
        return ResponseModel(
            success=True,
            message="搜索成功",
            data=result,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except Exception as e:
        logger.error(f"搜索知识库失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索知识库失败: {str(e)}"
        )


@router.get("/{knowledge_id}", response_model=ResponseModel)
async def get_knowledge(
    knowledge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取知识条目详情"""
    try:
        knowledge = db.query(BusinessKnowledge).filter(
            BusinessKnowledge.id == knowledge_id,
            BusinessKnowledge.is_deleted == False
        ).first()
        
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在"
            )
        
        # 解析标签
        tags_list = []
        if knowledge.tags:
            tags_list = [t.strip() for t in knowledge.tags.split(",") if t.strip()]
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": knowledge.id,
                "title": knowledge.title,
                "content": knowledge.content,
                "category": knowledge.category,
                "tags": tags_list,
                "created_by": knowledge.created_by,
                "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None,
                "updated_at": knowledge.updated_at.isoformat() if knowledge.updated_at else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识条目详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识条目详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel)
@router.post("/", response_model=ResponseModel)
async def create_knowledge(
    knowledge_data: BusinessKnowledgeCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建知识条目"""
    try:
        # 创建知识条目
        knowledge = BusinessKnowledge(
            title=knowledge_data.title,
            content=knowledge_data.content,
            category=knowledge_data.category,
            tags=knowledge_data.tags,
            created_by=current_user.id
        )
        
        db.add(knowledge)
        db.commit()
        db.refresh(knowledge)
        
        logger.info(f"用户 {current_user.username} 创建知识条目: {knowledge_data.title}")
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": knowledge.id,
                "title": knowledge.title
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"创建知识条目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识条目失败: {str(e)}"
        )


@router.put("/{knowledge_id}", response_model=ResponseModel)
async def update_knowledge(
    knowledge_id: int,
    knowledge_data: BusinessKnowledgeUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新知识条目"""
    try:
        knowledge = db.query(BusinessKnowledge).filter(
            BusinessKnowledge.id == knowledge_id,
            BusinessKnowledge.is_deleted == False
        ).first()
        
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在"
            )
        
        # 更新字段
        update_data = {}
        if knowledge_data.title is not None:
            update_data["title"] = knowledge_data.title
        if knowledge_data.content is not None:
            update_data["content"] = knowledge_data.content
        if knowledge_data.category is not None:
            update_data["category"] = knowledge_data.category
        if knowledge_data.tags is not None:
            update_data["tags"] = knowledge_data.tags
        
        # 执行更新
        db.query(BusinessKnowledge).filter(BusinessKnowledge.id == knowledge_id).update(update_data)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 更新知识条目: {knowledge_id}")
        
        return ResponseModel(
            success=True,
            message="更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新知识条目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识条目失败: {str(e)}"
        )


@router.delete("/{knowledge_id}", response_model=ResponseModel)
async def delete_knowledge(
    knowledge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除知识条目"""
    try:
        knowledge = db.query(BusinessKnowledge).filter(
            BusinessKnowledge.id == knowledge_id,
            BusinessKnowledge.is_deleted == False
        ).first()
        
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目不存在"
            )
        
        if knowledge.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识条目已被删除"
            )
        
        # 软删除
        knowledge.is_deleted = True
        db.commit()
        
        logger.info(f"用户 {current_user.username} 软删除知识条目: {knowledge.title}")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除知识条目失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识条目失败: {str(e)}"
        )


@router.get("/categories/list", response_model=ResponseModel)
async def list_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有分类列表"""
    try:
        # 查询所有不重复的分类
        categories = db.query(BusinessKnowledge.category).filter(
            BusinessKnowledge.is_deleted == False
        ).filter(
            BusinessKnowledge.category.isnot(None),
            BusinessKnowledge.category != ""
        ).distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=sorted(category_list)
        )
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类列表失败: {str(e)}"
        )


@router.get("/tags/list", response_model=ResponseModel)
async def list_tags(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有标签列表"""
    try:
        # 查询所有有标签的记录
        knowledge_list = db.query(BusinessKnowledge.tags).filter(
            BusinessKnowledge.is_deleted == False
        ).filter(
            BusinessKnowledge.tags.isnot(None),
            BusinessKnowledge.tags != ""
        ).all()
        
        # 收集所有标签
        all_tags = set()
        for item in knowledge_list:
            if item[0]:
                tags = [t.strip() for t in item[0].split(",") if t.strip()]
                all_tags.update(tags)
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=sorted(list(all_tags))
        )
    except Exception as e:
        logger.error(f"获取标签列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签列表失败: {str(e)}"
        )


