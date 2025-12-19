"""
推荐问题API
基于SQL示例库、历史对话和数据源推荐问题
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from loguru import logger

from app.core.database import get_local_db
from app.models import User, ChatSession, ChatMessage, SQLExample, DatabaseConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user

router = APIRouter(prefix="/api/v1/chat", tags=["对话推荐"])


@router.get("/sessions/{session_id}/recommended-questions", response_model=ResponseModel)
async def get_recommended_questions(
    session_id: int,
    limit: int = Query(5, ge=1, le=20, description="返回数量限制"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """
    获取推荐问题
    
    Args:
        session_id: 对话会话ID
        limit: 返回数量限制
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        推荐问题列表
    """
    try:
        # 1. 验证会话
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        recommended_questions = []
        
        # 2. 基于SQL示例库推荐
        sql_examples = db.query(SQLExample).limit(limit * 2).all()
        
        for example in sql_examples:
            # 优先使用 question，如果没有则使用 description
            question_text = example.question or example.description
            if question_text:
                recommended_questions.append(question_text)
        
        # 3. 基于历史对话推荐（如果有）
        if session.data_source_id:
            # 获取该数据源的历史对话问题
            history_sessions = db.query(ChatSession).filter(
                ChatSession.user_id == current_user.id,
                ChatSession.data_source_id == session.data_source_id,
                ChatSession.id != session_id
            ).order_by(ChatSession.created_at.desc()).limit(limit).all()
            
            for hist_session in history_sessions:
                # 获取该会话的第一个用户消息
                first_message = db.query(ChatMessage).filter(
                    ChatMessage.session_id == hist_session.id,
                    ChatMessage.role == "user"
                ).order_by(ChatMessage.created_at.asc()).first()
                
                if first_message and first_message.content:
                    recommended_questions.append(first_message.content)
        
        # 4. 基于数据源推荐（如果有表信息）
        if session.data_source_id:
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == session.data_source_id
            ).first()
            
            if db_config:
                # 生成一些通用问题模板
                common_questions = [
                    f"查询{db_config.name}中的所有表",
                    f"统计{db_config.name}中的数据量",
                    f"查看{db_config.name}的表结构"
                ]
                recommended_questions.extend(common_questions)
        
        # 去重并限制数量
        unique_questions = []
        seen = set()
        for q in recommended_questions:
            if q not in seen and len(q.strip()) > 0:
                seen.add(q)
                unique_questions.append(q)
                if len(unique_questions) >= limit:
                    break
        
        return ResponseModel(
            success=True,
            message="获取推荐问题成功",
            data=unique_questions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐问题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐问题失败: {str(e)}")

