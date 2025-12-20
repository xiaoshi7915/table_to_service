"""
推荐问题API
基于SQL示例库、历史对话和数据源推荐问题
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.database import get_local_db
from app.models import User, ChatSession, ChatMessage, SQLExample, DatabaseConfig, AIModelConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.llm.factory import LLMFactory

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


async def generate_dynamic_recommendations(
    session_id: int,
    current_question: str,
    sql: Optional[str] = None,
    data: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Session] = None,
    current_user: Optional[User] = None,
    selected_tables: Optional[List[str]] = None,
    llm_client: Optional[Any] = None
) -> List[str]:
    """
    基于会话上下文动态生成推荐问题
    
    Args:
        session_id: 会话ID
        current_question: 当前用户问题
        sql: 生成的SQL语句
        data: SQL执行结果数据
        db: 数据库会话
        current_user: 当前用户
        selected_tables: 当前会话选择的表列表
        
    Returns:
        推荐问题列表（最多3个）
    """
    try:
        if not db:
            return []
        
        recommendations = []
        
        # 获取会话信息（包含数据源和选择的表）
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return []
        
        # 获取数据源信息
        db_config = None
        if session.data_source_id:
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == session.data_source_id
            ).first()
        
        # 获取选择的表列表（优先使用传入的参数，否则从会话中获取）
        if not selected_tables and session.selected_tables:
            try:
                import json
                selected_tables = json.loads(session.selected_tables)
            except:
                selected_tables = []
        
        # 1. 基于当前会话的表和数据源生成推荐问题（避免查询所有数据明细）
        if selected_tables and len(selected_tables) > 0:
            # 基于选择的表生成推荐问题（避免"查询所有数据"）
            for table in selected_tables[:3]:
                if table:
                    # 生成基于表的推荐问题（使用聚合查询，避免查询所有明细）
                    recommendations.append(f"统计{table}表中的记录数")
                    recommendations.append(f"查询{table}表的数据概览")
                    recommendations.append(f"查看{table}表的汇总信息")
                    if len(recommendations) >= 3:
                        break
        
        # 2. 基于当前SQL和数据特征生成推荐问题
        if sql and data:
            # 分析数据特征，生成相关问题
            if len(data) > 0:
                # 获取数据列名
                columns = list(data[0].keys()) if data else []
                
                # 基于列名生成推荐问题
                if len(columns) >= 2:
                    # 如果有数值列，推荐聚合查询
                    numeric_patterns = ['count', 'sum', 'avg', 'max', 'min', 'total', 'amount', 'price', '数量', '金额', '价格']
                    has_numeric = any(any(pattern in col.lower() for pattern in numeric_patterns) for col in columns)
                    
                    if has_numeric:
                        # 推荐聚合分析问题
                        recommendations.append(f"按{columns[0]}分组统计{columns[1]}")
                        recommendations.append(f"查看{columns[0]}的分布情况")
                
                # 基于当前问题生成相关问题（避免查询所有明细）
                if "统计" in current_question or "count" in sql.lower():
                    # 不推荐"查看详细列表"，而是推荐其他聚合查询
                    if len(columns) >= 2:
                        recommendations.append(f"按{columns[0]}分组统计{columns[1]}")
                elif "查询" in current_question or "select" in sql.lower():
                    if "group" in sql.lower() or "分组" in current_question:
                        # 已经是分组查询，推荐其他维度的分析
                        if len(columns) >= 2:
                            recommendations.append(f"查看{columns[0]}的TOP 10数据")
                    else:
                        # 不是分组查询，推荐分组统计
                        recommendations.append(f"按{columns[0] if columns else '某个字段'}分组统计")
        
        # 3. 基于会话历史生成推荐问题
        if db and session_id:
            # 获取会话中的最近几条消息
            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user"
            ).order_by(ChatMessage.created_at.desc()).limit(3).all()
            
            # 基于历史问题生成相关问题
            for msg in recent_messages:
                if msg.content and msg.content != current_question:
                    # 简单的问题变换
                    if "统计" in msg.content:
                        recommendations.append(msg.content.replace("统计", "查看"))
                    elif "查看" in msg.content:
                        recommendations.append(msg.content.replace("查看", "统计"))
        
        # 4. 基于SQL示例库推荐（如果推荐问题不足，优先推荐与当前数据源相关的示例）
        if len(recommendations) < 3 and db:
            # 如果知道数据源类型，优先推荐匹配的SQL示例
            db_type_filter = None
            if db_config:
                db_type_filter = db_config.db_type
            
            query = db.query(SQLExample)
            if db_type_filter:
                query = query.filter(SQLExample.db_type == db_type_filter)
            
            sql_examples = query.limit(5).all()
            sql_examples = db.query(SQLExample).limit(5).all()
            for example in sql_examples:
                question_text = example.question or example.description
                if question_text and question_text not in recommendations:
                    recommendations.append(question_text)
                    if len(recommendations) >= 3:
                        break
        
        # 4. 优先使用LLM生成推荐问题（如果提供了LLM客户端）
        if llm_client and sql:
            try:
                # 获取会话历史消息（用于上下文）
                session_history = []
                if db and session_id:
                    recent_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session_id
                    ).order_by(ChatMessage.created_at.desc()).limit(5).all()
                    
                    for msg in reversed(recent_messages):  # 按时间正序
                        if msg.role == "user":
                            session_history.append(f"用户：{msg.content}")
                        elif msg.role == "assistant" and msg.content:
                            session_history.append(f"助手：{msg.content[:200]}")  # 只取前200字
                
                # 构建数据摘要
                data_summary = ""
                if data and len(data) > 0:
                    columns = list(data[0].keys()) if data else []
                    data_summary = f"查询结果：共{len(data)}条数据，包含列：{', '.join(columns[:8])}"
                    if len(columns) > 8:
                        data_summary += f"等{len(columns)}个字段"
                else:
                    data_summary = "查询结果：无数据"
                
                # 构建表信息
                table_info = ""
                if selected_tables and len(selected_tables) > 0:
                    table_info = f"当前会话涉及的表：{', '.join(selected_tables[:5])}"
                elif db_config:
                    table_info = f"数据源：{db_config.name}"
                
                # 构建提示词
                prompt = f"""你是一个智能数据分析助手。基于以下对话上下文，生成3个相关的、个性化的推荐问题。

对话上下文：
{chr(10).join(session_history) if session_history else '这是对话的开始'}

当前用户问题：{current_question}
执行的SQL：{sql[:300]}
{table_info}
{data_summary}

请生成3个推荐问题，要求：
1. **问题要具体、可执行**，基于当前数据源和表结构
2. **角度要多样化**：可以是更深入的分析、不同维度的统计、时间趋势、对比分析等
3. **避免重复**：不要生成"数据概览"、"汇总信息"等通用问题
4. **基于上下文**：结合当前问题和查询结果，生成有意义的后续问题
5. **语言自然**：使用自然的中文表达，不要过于技术化

只返回3个问题，每行一个问题，不要编号，不要添加任何前缀或说明文字："""
                
                # 调用LLM生成推荐问题
                messages = [{"role": "user", "content": prompt}]
                response = await llm_client.chat_completion(
                    messages=messages,
                    temperature=0.8,  # 稍高的温度以获得更多样化的问题
                    max_tokens=300
                )
                
                # 解析LLM返回的问题
                if isinstance(response, dict):
                    llm_content = response.get("content", "").strip() or response.get("message", {}).get("content", "").strip()
                else:
                    llm_content = str(response).strip()
                
                if llm_content:
                    # 按行分割，提取问题
                    llm_questions = []
                    for line in llm_content.split('\n'):
                        line = line.strip()
                        # 移除可能的编号（如"1. "、"1、"等）
                        line = line.lstrip('0123456789.、）)').strip()
                        # 移除可能的标记（如"- "、"• "等）
                        line = line.lstrip('- •*').strip()
                        if line and len(line) > 5 and len(line) < 100:  # 过滤太短或太长的问题
                            # 过滤掉明显的通用问题
                            if not any(keyword in line for keyword in ["数据概览", "汇总信息", "查看所有", "查询全部"]):
                                llm_questions.append(line)
                    
                    if len(llm_questions) > 0:
                        # 使用LLM生成的问题，替换规则生成的问题
                        recommendations = llm_questions[:3]
                        logger.info(f"使用LLM生成推荐问题成功，共{len(recommendations)}个")
                    else:
                        logger.warning("LLM返回的问题格式不正确，使用规则生成")
                else:
                    logger.warning("LLM返回内容为空，使用规则生成")
                    
            except Exception as e:
                logger.warning(f"使用LLM生成推荐问题失败: {e}，将使用规则生成")
        
        # 5. 去重并限制数量
        unique_recommendations = []
        seen = set()
        for rec in recommendations:
            if rec and rec not in seen and len(rec.strip()) > 0:
                seen.add(rec)
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= 3:
                    break
        
        return unique_recommendations[:3]
        
    except Exception as e:
        logger.error(f"生成动态推荐问题失败: {e}", exc_info=True)
        # 返回空列表，不抛出异常
        return []

