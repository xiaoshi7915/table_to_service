"""
对话API
实现对话会话和消息管理
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import desc, func
from loguru import logger
from datetime import datetime
import json
import asyncio

from app.core.database import get_local_db
from app.core.security import get_current_active_user
from app.models import User, ChatSession, ChatMessage, DatabaseConfig, AIModelConfig, Terminology, SQLExample, BusinessKnowledge
from app.schemas import ResponseModel
from app.core.llm.factory import LLMFactory
from app.api.v1.chat_recommendations import generate_dynamic_recommendations
from app.core.rag_langchain.question_rewriter import QuestionRewriter
from app.core.performance_monitor import get_performance_monitor, track_time

router = APIRouter(prefix="/api/v1/chat", tags=["对话"])


async def generate_session_title(
    session: ChatSession,
    first_question: str,
    db: Session,
    llm_client: Any
) -> None:
    """
    根据对话内容自动生成会话标题
    
    Args:
        session: 会话对象
        first_question: 第一条用户问题
        db: 数据库会话
        llm_client: LLM客户端
    """
    try:
        # 构建生成标题的提示词
        title_prompt = f"""根据以下用户问题，生成一个简洁、准确的对话标题。

要求：
1. 标题长度控制在10-20个汉字
2. 标题要能准确概括问题的核心内容
3. 使用简洁明了的语言
4. 不要包含"对话"、"问数"等冗余词汇
5. 直接返回标题，不要包含其他说明文字

用户问题：{first_question}

标题："""
        
        # 调用LLM生成标题
        messages = [{"role": "user", "content": title_prompt}]
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=50  # 标题不需要太多token
        )
        
        # 提取标题
        if isinstance(response, dict):
            generated_title = response.get("content", "").strip() or response.get("message", {}).get("content", "").strip()
        else:
            generated_title = str(response).strip()
        
        # 清理标题（移除可能的引号、换行等）
        generated_title = generated_title.replace('"', '').replace("'", "").replace("\n", "").strip()
        
        # 如果标题为空或过长，使用备用标题
        if not generated_title or len(generated_title) > 50:
            # 从问题中提取关键词作为标题
            if len(first_question) <= 20:
                generated_title = first_question
            else:
                generated_title = first_question[:20] + "..."
        
        # 更新会话标题（确保使用传入的数据库会话）
        session.title = generated_title
        # 将更改添加到会话（确保 SQLAlchemy 跟踪更改）
        db.merge(session)
        logger.info(f"自动生成对话标题: {generated_title} (会话ID: {session.id})")
        
    except Exception as e:
        logger.error(f"生成对话标题失败: {e}", exc_info=True)
        # 生成失败时，使用问题作为标题（截取前20个字符）
        if len(first_question) <= 20:
            session.title = first_question
        else:
            session.title = first_question[:20] + "..."


async def generate_data_summary(
    question: str,
    sql: str,
    data: List[Dict[str, Any]],
    llm_client: Any
) -> Optional[str]:
    """
    使用LLM对SQL执行结果进行总结分析，生成文字描述
    
    Args:
        question: 用户问题
        sql: 执行的SQL语句
        data: SQL执行结果数据
        llm_client: LLM客户端
        
    Returns:
        数据总结分析的文字描述，如果生成失败则返回None
    """
    try:
        # 即使数据为空，也生成说明
        if not data or len(data) == 0:
            # 为空数据生成说明
            empty_prompt = f"""你是一个数据分析助手。用户执行了以下SQL查询，但查询结果为空（没有找到符合条件的记录）。

用户问题：{question}
执行的SQL：{sql}

请生成一段简洁的中文说明，解释查询结果为空可能的原因，或者说明当前数据状态。要求：
1. 用简洁明了的语言
2. 直接返回说明，不要包含"总结"、"分析"等前缀词
3. 长度控制在50-100字

说明："""
            
            messages = [{"role": "user", "content": empty_prompt}]
            response = await llm_client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            if isinstance(response, dict):
                summary = response.get("content", "").strip() or response.get("message", {}).get("content", "").strip()
            else:
                summary = str(response).strip()
            
            if summary and len(summary) > 10:
                return summary
            return "查询结果显示没有找到符合条件的记录。"
        
        # 限制数据量，避免token过多（只使用前20条数据进行分析）
        sample_data = data[:20]
        total_count = len(data)
        
        # 获取数据列名
        columns = list(sample_data[0].keys()) if sample_data else []
        
        # 构建数据摘要（只包含关键信息，避免数据过多）
        data_summary = []
        for i, row in enumerate(sample_data[:10]):  # 只展示前10条作为示例
            row_str = ", ".join([f"{k}: {v}" for k, v in list(row.items())[:5]])  # 每行只展示前5个字段
            data_summary.append(f"第{i+1}条: {row_str}")
        
        # 检查数据是否全为0或空值
        all_zero = True
        for row in sample_data[:5]:
            for key, value in row.items():
                if value is not None and value != 0 and value != "" and str(value).lower() != "null":
                    all_zero = False
                    break
            if not all_zero:
                break
        
        # 构建提示词
        if all_zero and total_count > 0:
            # 如果数据全为0，生成特殊说明
            summary_prompt = f"""你是一个数据分析助手。用户执行了以下SQL查询，查询返回了{total_count}条记录，但所有数值都为0。

用户问题：{question}
执行的SQL：{sql}
查询结果：共{total_count}条记录，所有数值字段都为0

请生成一段简洁的中文说明，解释这个结果的含义。要求：
1. 说明查询结果的含义（比如"查询结果显示没有符合条件的记录"或"当前数据中该指标为0"）
2. 用简洁明了的语言，直接回答用户的问题
3. 直接返回说明，不要包含"总结"、"分析"等前缀词
4. 长度控制在100-150字

说明："""
        else:
            summary_prompt = f"""你是一个数据分析助手。请对以下SQL查询结果进行总结分析，生成一段简洁、准确的中文文字描述。

用户问题：{question}
执行的SQL：{sql}

查询结果：
- 总记录数：{total_count}条
- 数据列：{', '.join(columns[:10])}
- 示例数据（前10条）：
{chr(10).join(data_summary)}

请生成一段200-300字的数据分析总结，要求：
1. 概括数据的主要特征和关键信息
2. 指出数据的分布情况、趋势或异常
3. 用简洁明了的语言，避免技术术语
4. 直接返回分析结果，不要包含"总结"、"分析"等前缀词
5. 如果数据量很大，可以说明数据规模

数据分析："""
        
        # 调用LLM生成总结
        messages = [{"role": "user", "content": summary_prompt}]
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500  # 总结需要更多token
        )
        
        # 提取总结内容
        if isinstance(response, dict):
            summary = response.get("content", "").strip() or response.get("message", {}).get("content", "").strip()
        else:
            summary = str(response).strip()
        
        if summary and len(summary) > 10:  # 确保有实际内容
            logger.info(f"生成数据总结成功，长度: {len(summary)}")
            return summary
        else:
            logger.warning("LLM返回的数据总结为空或过短")
            return None
            
    except Exception as e:
        logger.warning(f"生成数据总结失败: {e}，不影响主流程")
        return None


# 请求模型
class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = None
    data_source_id: Optional[int] = None
    selected_tables: Optional[List[str]] = None  # 用户选择的表列表


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = None
    selected_tables: Optional[List[str]] = None  # 用户选择的表列表


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    question: str
    data_source_id: Optional[int] = None
    selected_tables: Optional[List[str]] = None  # 用户选择的表列表
    edited_sql: Optional[str] = None  # 用户编辑后的SQL（用于重试）


# 响应模型
class SessionResponse(BaseModel):
    """会话响应"""
    id: int
    title: str
    data_source_id: Optional[int]
    data_source_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    session_id: int
    role: str
    content: str
    sql: Optional[str]
    chart_type: Optional[str]
    chart_config: Optional[Dict[str, Any]]
    data: Optional[List[Dict[str, Any]]]
    tokens_used: Optional[int]
    created_at: datetime


@router.post("/sessions", response_model=ResponseModel)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建对话会话"""
    try:
        # 生成默认标题（如果未提供，使用时间戳作为临时标题，后续会根据对话内容自动生成）
        if not request.title:
            request.title = f"新对话 {datetime.now().strftime('%m-%d %H:%M')}"
        
        # 验证数据源
        data_source_id = request.data_source_id
        if data_source_id:
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == data_source_id,
                DatabaseConfig.user_id == current_user.id
            ).first()
            if not db_config:
                raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 保存选择的表列表（JSON格式）
        selected_tables_json = None
        if request.selected_tables:
            selected_tables_json = json.dumps(request.selected_tables, ensure_ascii=False)
        
        # 创建会话
        session = ChatSession(
            user_id=current_user.id,
            title=request.title,
            data_source_id=data_source_id,
            selected_tables=selected_tables_json,
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return ResponseModel(
            success=True,
            message="会话创建成功",
            data={
                "id": session.id,
                "title": session.title,
                "data_source_id": session.data_source_id,
                "created_at": session.created_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/sessions", response_model=ResponseModel)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    data_source_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),  # 搜索关键词
    start_date: Optional[str] = Query(None),  # 开始日期
    end_date: Optional[str] = Query(None),  # 结束日期
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取会话列表"""
    try:
        query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
        
        # 状态筛选
        if status:
            query = query.filter(ChatSession.status == status)
        
        # 数据源筛选
        if data_source_id:
            query = query.filter(ChatSession.data_source_id == data_source_id)
        
        # 关键词搜索（标题）
        if keyword:
            query = query.filter(ChatSession.title.like(f"%{keyword}%"))
        
        # 日期范围筛选
        if start_date:
            from datetime import datetime
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(ChatSession.created_at >= start_dt)
            except:
                pass
        
        if end_date:
            from datetime import datetime
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(ChatSession.created_at <= end_dt)
            except:
                pass
        
        # 总数
        total = query.count()
        
        # 分页
        sessions = query.order_by(desc(ChatSession.updated_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 优化：批量获取数据源名称和消息数量（避免N+1查询）
        session_ids = [s.id for s in sessions]
        data_source_ids = [s.data_source_id for s in sessions if s.data_source_id]
        
        # 批量查询数据源名称
        db_configs_map = {}
        if data_source_ids:
            db_configs = db.query(DatabaseConfig).filter(
                DatabaseConfig.id.in_(data_source_ids)
            ).all()
            db_configs_map = {cfg.id: cfg.name for cfg in db_configs}
        
        # 批量查询消息数量（使用聚合查询）
        message_counts_map = {}
        if session_ids:
            message_counts = db.query(
                ChatMessage.session_id,
                func.count(ChatMessage.id).label('count')
            ).filter(
                ChatMessage.session_id.in_(session_ids)
            ).group_by(ChatMessage.session_id).all()
            message_counts_map = {session_id: count for session_id, count in message_counts}
        
        # 构建响应数据
        session_list = []
        for session in sessions:
            data_source_name = db_configs_map.get(session.data_source_id) if session.data_source_id else None
            message_count = message_counts_map.get(session.id, 0)
            
            session_list.append({
                "id": session.id,
                "title": session.title,
                "data_source_id": session.data_source_id,
                "data_source_name": data_source_name,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": message_count
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=session_list,
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        )
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=ResponseModel)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取会话详情"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取数据源名称
        data_source_name = None
        if session.data_source_id:
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == session.data_source_id
            ).first()
            if db_config:
                data_source_name = db_config.name
        
        # 获取消息数量
        message_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).count()
        
        # 解析selected_tables
        selected_tables = None
        if session.selected_tables:
            try:
                selected_tables = json.loads(session.selected_tables)
            except:
                pass
        
        # 获取表描述信息（如果会话有数据源和选择的表）
        table_info = []
        if session.data_source_id and selected_tables:
            try:
                from app.core.db_factory import DatabaseConnectionFactory
                from sqlalchemy import inspect, text
                
                db_config = db.query(DatabaseConfig).filter(
                    DatabaseConfig.id == session.data_source_id
                ).first()
                
                if db_config:
                    db_type = db_config.db_type or "mysql"
                    engine = DatabaseConnectionFactory.create_engine(db_config)
                    
                    try:
                        for table_name in selected_tables:
                            table_desc = {"name": table_name, "description": ""}
                            
                            # 尝试获取表注释/描述
                            try:
                                if db_type == "mysql":
                                    with engine.connect() as conn:
                                        comment_query = text("""
                                            SELECT TABLE_COMMENT 
                                            FROM INFORMATION_SCHEMA.TABLES 
                                            WHERE TABLE_SCHEMA = :db_name 
                                            AND TABLE_NAME = :table_name
                                        """)
                                        result = conn.execute(comment_query, {
                                            "db_name": db_config.database,
                                            "table_name": table_name
                                        })
                                        row = result.fetchone()
                                        if row and row[0]:
                                            table_desc["description"] = row[0]
                                elif db_type == "postgresql":
                                    with engine.connect() as conn:
                                        comment_query = text("""
                                            SELECT obj_description(c.oid, 'pg_class') as table_comment
                                            FROM pg_class c
                                            JOIN pg_namespace n ON c.relnamespace = n.oid
                                            WHERE c.relname = :table_name 
                                            AND n.nspname = 'public'
                                        """)
                                        result = conn.execute(comment_query, {"table_name": table_name})
                                        row = result.fetchone()
                                        if row and row[0]:
                                            table_desc["description"] = row[0]
                            except Exception as e:
                                logger.debug(f"获取表 {table_name} 注释失败: {e}")
                            
                            table_info.append(table_desc)
                        
                        engine.dispose()
                    except Exception as e:
                        engine.dispose()
                        logger.warning(f"获取表描述信息失败: {e}")
            except Exception as e:
                logger.debug(f"获取表描述信息失败: {e}")
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": session.id,
                "title": session.title,
                "data_source_id": session.data_source_id,
                "data_source_name": data_source_name,
                "selected_tables": selected_tables,
                "table_info": table_info,  # 表信息（包含描述）
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": message_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.put("/sessions/{session_id}", response_model=ResponseModel)
async def update_session(
    session_id: int,
    request: UpdateSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新会话（重命名或更新选择的表）"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 更新标题（如果提供）
        if request.title is not None:
            session.title = request.title
        
        # 更新选择的表（如果提供）
        if request.selected_tables is not None:
            import json
            session.selected_tables = json.dumps(request.selected_tables, ensure_ascii=False)
        
        db.commit()
        db.refresh(session)
        
        # 解析selected_tables用于返回
        selected_tables = None
        if session.selected_tables:
            try:
                selected_tables = json.loads(session.selected_tables)
            except:
                pass
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={
                "id": session.id,
                "title": session.title,
                "selected_tables": selected_tables
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新会话失败: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=ResponseModel)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除会话"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 删除会话会级联删除所有消息（通过外键约束）
        db.delete(session)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.post("/sessions/batch-delete", response_model=ResponseModel)
async def batch_delete_sessions(
    session_ids: List[int] = Body(..., embed=True, alias="session_ids"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """批量删除会话"""
    try:
        if not session_ids:
            raise HTTPException(status_code=400, detail="请选择要删除的会话")
        
        # 验证所有权
        sessions = db.query(ChatSession).filter(
            ChatSession.id.in_(session_ids),
            ChatSession.user_id == current_user.id
        ).all()
        
        if len(sessions) != len(session_ids):
            raise HTTPException(status_code=403, detail="部分会话不存在或无权限")
        
        # 批量删除
        for session in sessions:
            db.delete(session)
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message=f"成功删除 {len(sessions)} 个会话"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量删除会话失败: {str(e)}")


@router.post("/sessions/{session_id}/messages", response_model=ResponseModel)
async def send_message(
    session_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """发送消息并生成SQL"""
    with track_time("智能问数完整流程"):
        try:
            # 1. 验证会话
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
            
            # 2. 确定数据源
            data_source_id = request.data_source_id or session.data_source_id
            if not data_source_id:
                raise HTTPException(status_code=400, detail="请指定数据源")
            
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == data_source_id,
                DatabaseConfig.user_id == current_user.id
            ).first()
            
            if not db_config:
                raise HTTPException(status_code=404, detail="数据源不存在")
            
            # 3. 获取选择的表列表（优先使用请求中的，否则从会话中获取）
            selected_tables = request.selected_tables
            if not selected_tables and session.selected_tables:
                try:
                    selected_tables = json.loads(session.selected_tables)
                except:
                    selected_tables = None
            
            # 4. 问题改写（优化用户问题表述）
            rewritten_question = request.question
            question_rewrite_info = None
            try:
                # 创建问题改写服务（使用规则引擎，因为LLM需要异步调用）
                rewriter = QuestionRewriter(llm_client=None)
                
                # 构建上下文信息
                rewrite_context = {
                    "db_type": db_config.db_type or "mysql",
                    "table_names": selected_tables or []
                }
                
                # 获取术语映射（如果有）
                if selected_tables:
                    terminologies = db.query(Terminology).filter(
                        Terminology.table_name.in_(selected_tables)
                    ).all()
                    if terminologies:
                        terminology_map = {
                            t.business_term: t.db_field
                            for t in terminologies
                            if t.business_term and t.db_field
                        }
                        rewrite_context["terminology_map"] = terminology_map
                
                # 改写问题
                rewrite_result = rewriter.rewrite_question(
                    question=request.question,
                    context=rewrite_context
                )
                
                # 检查是否有权限警告
                warnings = rewrite_result.get("warnings", [])
                if warnings:
                    # 如果有警告，返回错误提示
                    return ResponseModel(
                        success=False,
                        message="问题包含不允许的操作",
                        data={
                            "error": warnings[0],
                            "warnings": warnings,
                            "can_retry": True,
                            "suggestion": "请修改您的问题，使用统计查询或添加筛选条件，避免查询所有数据明细或修改数据操作。"
                        }
                    )
                
                # 如果问题被改写，使用改写后的问题
                if rewrite_result.get("rewritten_question") and rewrite_result["rewritten_question"] != request.question:
                    rewritten_question = rewrite_result["rewritten_question"]
                    question_rewrite_info = {
                        "original": rewrite_result["original_question"],
                        "rewritten": rewrite_result["rewritten_question"],
                        "changes": rewrite_result.get("changes", []),
                        "method": rewrite_result.get("method", "rule")
                    }
                    logger.info(f"问题改写: {request.question} -> {rewritten_question}")
            except Exception as e:
                logger.warning(f"问题改写失败: {e}，使用原始问题")
                # 改写失败不影响主流程，继续使用原始问题
        
            # 5. 保存用户消息（保存原始问题，但使用改写后的问题进行SQL生成）
            user_message = ChatMessage(
                session_id=session_id,
                role="user",
                content=request.question  # 保存原始问题
            )
            db.add(user_message)
            db.commit()
            
            # 6. 获取AI模型配置
            model_config = db.query(AIModelConfig).filter(
                AIModelConfig.is_default == True,
                AIModelConfig.is_active == True
            ).first()
            
            if not model_config:
                raise HTTPException(status_code=400, detail="未配置默认AI模型")
        
            # 7. 创建LLM客户端
            llm_client = LLMFactory.create_client(model_config)
        
            # 8. 创建LangChain适配的LLM
            from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
            langchain_llm = LangChainLLMAdapter(llm_client)
        
            # 9. 创建RAG服务（使用LangChain版本）
            from app.core.rag_langchain.embedding_service import ChineseEmbeddingService
            from app.core.rag_langchain.vector_store import VectorStoreManager
            from app.core.rag_langchain.hybrid_retriever import HybridRetriever
            from app.core.rag_langchain.rag_workflow import RAGWorkflow
            from app.core.config import settings
            try:
                from langchain_core.documents import Document
                try:
                    from langchain_core.retrievers import BaseRetriever
                except ImportError:
                    from langchain.schema import BaseRetriever
            except ImportError:
                from langchain.schema import Document, BaseRetriever
        
            # 初始化嵌入服务（使用单例模式，避免重复加载模型）
            embedding_service = None
            try:
                embedding_service = ChineseEmbeddingService.get_instance()
                logger.info("使用中文嵌入模型（bge-base-zh-v1.5，单例模式）")
            except Exception as e:
                logger.warning(f"中文嵌入模型加载失败: {e}，将使用传统检索")
        
            # 初始化向量存储管理器
            vector_manager = None
            if embedding_service:
                try:
                    # 使用本地数据库连接字符串（需要是PostgreSQL）
                    connection_string = settings.local_database_url
                    if "postgresql" in connection_string.lower():
                        vector_manager = VectorStoreManager(connection_string, embedding_service)
                        logger.info("✅ 向量存储管理器初始化成功（使用pgvector）")
                    else:
                        # 非PostgreSQL数据库，向量存储功能不可用，但不影响基本功能
                        db_type = "MySQL" if "mysql" in connection_string.lower() else "其他数据库"
                        logger.info(f"ℹ️  向量存储功能需要PostgreSQL数据库（pgvector扩展），当前本地数据库为{db_type}。系统将使用简化检索模式，功能正常但检索精度可能略低")
                        vector_manager = None
                except Exception as e:
                    logger.warning(f"向量存储管理器初始化失败: {e}，将使用简化检索模式")
                    vector_manager = None
        
            # 创建检索器
            terminology_retriever = None
            sql_example_retriever = None
            knowledge_retriever = None
        
            if vector_manager:
                try:
                    # 并行加载文档用于BM25检索（优化性能）
                    import concurrent.futures
                    
                    # 优化：只查询相关的数据（如果指定了表名）
                    def query_terminologies():
                        query = db.query(Terminology)
                        if selected_tables:
                            query = query.filter(Terminology.table_name.in_(selected_tables))
                        return query.all()
                    
                    def query_sql_examples():
                        query = db.query(SQLExample)
                        if selected_tables:
                            query = query.filter(
                                (SQLExample.table_name.in_(selected_tables)) |
                                (SQLExample.table_name.is_(None))
                            )
                        # 只查询当前数据库类型的示例
                        if db_config.db_type:
                            query = query.filter(SQLExample.db_type == db_config.db_type)
                        return query.all()
                    
                    def query_knowledge():
                        return db.query(BusinessKnowledge).all()
                    
                    # 使用线程池并行执行查询
                    try:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                            term_future = executor.submit(query_terminologies)
                            sql_future = executor.submit(query_sql_examples)
                            knowledge_future = executor.submit(query_knowledge)
                            
                            terminologies = term_future.result()
                            sql_examples = sql_future.result()
                            knowledge_items = knowledge_future.result()
                    except Exception as e:
                        logger.warning(f"并行查询失败，降级到串行查询: {e}")
                        # 降级到串行查询
                        terminologies = query_terminologies()
                        sql_examples = query_sql_examples()
                        knowledge_items = query_knowledge()
                    
                    # 转换为LangChain Document
                    term_docs = [
                        Document(
                            page_content=f"{t.business_term} {t.description or ''} {t.db_field}",
                            metadata={"id": t.id, "type": "terminology"}
                        )
                        for t in terminologies
                    ]
                    
                    sql_docs = [
                        Document(
                            page_content=f"{e.question} {e.description or ''} {e.sql_statement}",
                            metadata={"id": e.id, "type": "sql_example", "db_type": e.db_type}
                        )
                        for e in sql_examples
                    ]
                    
                    knowledge_docs = [
                        Document(
                            page_content=f"{k.title} {k.content}",
                            metadata={"id": k.id, "type": "knowledge", "category": k.category}
                        )
                        for k in knowledge_items
                    ]
                    
                    # 创建混合检索器（仅在向量存储可用时）
                    if term_docs:
                        term_store = vector_manager.get_store("terminologies")
                        if term_store:
                            terminology_retriever = HybridRetriever(
                                vector_store=term_store,
                                documents=term_docs
                            )
                    
                    if sql_docs:
                        sql_store = vector_manager.get_store("sql_examples")
                        if sql_store:
                            sql_example_retriever = HybridRetriever(
                                vector_store=sql_store,
                                documents=sql_docs
                            )
                    
                    if knowledge_docs:
                        knowledge_store = vector_manager.get_store("knowledge")
                        if knowledge_store:
                            knowledge_retriever = HybridRetriever(
                                vector_store=knowledge_store,
                                documents=knowledge_docs
                            )
                    
                except Exception as e:
                    logger.warning(f"创建检索器失败: {e}，将使用简化版本")
            
            # 如果检索器创建失败，使用空检索器（降级方案）
            if not terminology_retriever:
                try:
                    from langchain_core.retrievers import BaseRetriever
                except ImportError:
                    from langchain.schema import BaseRetriever
            
            class EmptyRetriever(BaseRetriever):
                def _get_relevant_documents(self, query: str):
                    return []
                async def _aget_relevant_documents(self, query: str):
                    return []
                def get_relevant_documents(self, query: str):
                    return []
                async def aget_relevant_documents(self, query: str):
                    return []
            
            terminology_retriever = EmptyRetriever()
            sql_example_retriever = EmptyRetriever()
            knowledge_retriever = EmptyRetriever()
        
            # 10. 创建RAG工作流
            rag_workflow = RAGWorkflow(
            llm=langchain_llm,
            terminology_retriever=terminology_retriever,
            sql_example_retriever=sql_example_retriever,
            knowledge_retriever=knowledge_retriever,
            max_retries=3
            )
        
            # 11. 运行工作流（使用改写后的问题，传递选择的表列表）
            workflow_result = rag_workflow.run(
            question=rewritten_question,  # 使用改写后的问题
            db_config=db_config,
            selected_tables=selected_tables  # 使用从会话或请求中获取的表列表
            )
        
            # 12. 提取结果
            # 确保workflow_result存在
            if not workflow_result:
                logger.warning("workflow_result为None，使用默认值")
                workflow_result = {}
            
            # 优先使用final_sql，如果没有则使用sql（确保SQL被正确提取）
            final_sql = workflow_result.get("final_sql") or workflow_result.get("sql", "")
            data = workflow_result.get("data", [])
            chart_config = workflow_result.get("chart_config")
            error = workflow_result.get("error")
            execution_error = workflow_result.get("execution_error")
            contains_complex_sql = workflow_result.get("contains_complex_sql", False)
            error_content = None  # 初始化error_content，避免未定义错误
            
            # 确保data和chart_config被初始化
            if data is None:
                data = []
            if chart_config is None:
                chart_config = {}
        
            # 记录日志，确保SQL被正确提取
            logger.info(f"提取结果：final_sql={final_sql[:100] if final_sql else '空'}, error={error}, execution_error={execution_error}, request.edited_sql={request.edited_sql if hasattr(request, 'edited_sql') else 'N/A'}")
        
            # 如果SQL包含复杂逻辑（如CREATE语句），返回友好提示和SQL
            if contains_complex_sql and final_sql:
                # 保存消息，包含SQL和友好提示
                assistant_message = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=f"""生成的SQL查询涉及复杂逻辑，需要创建临时表。为了数据安全，系统不会自动执行此类SQL。

**生成的SQL语句：**
```sql
{final_sql}
```

**说明：**
- 此SQL包含CREATE等语句，系统不会自动执行
- 您可以在数据库管理工具中手动执行此SQL
- 建议：如果可能，请尝试用更简单的查询方式重新提问，例如使用子查询或CTE（WITH子句）代替临时表""",
                    sql_statement=final_sql,
                    tokens_used=0
                )
                db.add(assistant_message)
                session.updated_at = datetime.now()
                db.commit()
                db.refresh(assistant_message)
                
                # 生成推荐问题
                recommended_questions = []
                try:
                    recommended_questions = await generate_dynamic_recommendations(
                        session_id=session_id,
                        current_question=request.question,
                        sql=final_sql,
                        data=None,
                        db=db,
                        current_user=current_user,
                        selected_tables=selected_tables
                    )
                except Exception as e:
                    logger.warning(f"生成动态推荐问题失败: {e}，将返回空列表")
                
                return ResponseModel(
                    success=True,
                    message="已生成SQL语句（需要手动执行）",
                    data={
                        "id": assistant_message.id,
                        "sql": final_sql,
                        "explanation": "生成的SQL涉及复杂逻辑，需要手动执行",
                        "contains_complex_sql": True,
                        "chart_type": None,
                        "chart_config": None,
                        "data": [],
                        "data_total": 0,
                        "tokens_used": 0,
                        "model": model_config.model_name,
                        "recommended_questions": recommended_questions
                    }
                )
            
            # 如果用户提供了编辑后的SQL，直接执行它
            if request.edited_sql:
                logger.info(f"用户提供了编辑后的SQL，准备执行: {request.edited_sql[:100] if request.edited_sql else '空'}")
                final_sql = request.edited_sql
                error = None
                execution_error = None
                data = []  # 初始化data变量
                chart_config = None  # 初始化chart_config变量
                try:
                    from app.core.rag_langchain.sql_executor import SQLExecutor
                    executor = SQLExecutor(
                        db_config=db_config,
                        timeout=30,
                        max_rows=1000,
                        enable_cache=True,  # 启用缓存
                        cache_ttl=600  # 10分钟
                    )
                    result = executor.execute(final_sql, user_id=current_user.id)
                    
                    if result["success"]:
                        data = result["data"]
                        # 重新生成图表配置
                        from app.core.rag_langchain.chart_service import ChartService
                        chart_service = ChartService()
                        chart_config = chart_service.generate_chart_config(
                            question=request.question,
                            data=data,
                            sql=final_sql
                        )
                        error = None
                        execution_error = None
                        # 设置workflow_result，确保后续流程能正常工作
                        if not workflow_result:
                            workflow_result = {}
                        workflow_result["explanation"] = f"用户编辑的SQL执行成功，返回 {len(data)} 条数据" if data else "用户编辑的SQL执行成功，但未返回数据"
                        workflow_result["data"] = data
                        workflow_result["chart_config"] = chart_config
                    else:
                        error = result.get("error", "SQL执行失败")
                        execution_error = error
                        data = []
                except Exception as e:
                    logger.error(f"执行用户编辑的SQL失败: {e}", exc_info=True)
                    error = str(e)
                    execution_error = error
                    data = []
            else:
                logger.info(f"用户未提供编辑后的SQL，跳过SQL执行流程")
        
            # 如果有错误，返回错误信息但包含SQL，允许用户编辑重试或继续用自然语言提问
            logger.info(f"错误检查：error={error}, execution_error={execution_error}, error类型={type(error)}, execution_error类型={type(execution_error)}")
            if error or execution_error:
                logger.info(f"进入错误处理流程：error={error}, execution_error={execution_error}")
                # 使用LLM生成友好的错误回复
                error_content = None
                try:
                    # 构建错误提示词
                    error_prompt = f"""用户提问：{request.question}

生成的SQL语句：
{final_sql if final_sql else '无'}

SQL执行失败，错误信息：{execution_error or error}

请生成一个友好、专业的错误回复，要求：
1. 用通俗易懂的语言解释错误原因
2. 如果SQL包含CREATE等语句，说明系统不允许执行此类操作，建议使用子查询或CTE代替临时表
3. 提供清晰的解决建议
4. 语气要友好、有帮助性
5. 不要使用技术术语，用用户能理解的语言
6. 在回复中明确显示生成的SQL语句

请直接返回回复内容，不要包含其他格式："""
                    
                    # 调用LLM生成友好回复（异步）
                    messages = [{"role": "user", "content": error_prompt}]
                    llm_response = await llm_client.chat_completion(
                        messages,
                        temperature=0.7,
                        max_tokens=400
                    )
                    
                    # 解析响应
                    if isinstance(llm_response, dict):
                        error_content = llm_response.get("content", "") or llm_response.get("message", {}).get("content", "")
                    else:
                        error_content = str(llm_response)
                    
                    # 清理响应
                    error_content = error_content.strip()
                    # 移除可能的Markdown格式
                    import re
                    error_content = re.sub(r'^```.*?\n', '', error_content, flags=re.DOTALL)
                    error_content = re.sub(r'\n```.*?$', '', error_content, flags=re.DOTALL)
                    error_content = error_content.strip()
                    
                    # 如果LLM回复为空，使用默认回复
                    if not error_content:
                        error_content = None
                        
                except Exception as e:
                    logger.warning(f"使用LLM生成友好错误回复失败: {e}，将使用默认回复")
                    error_content = None
                
                # 如果LLM生成失败，使用默认回复
                if not error_content:
                    error_content = f"""很抱歉，SQL执行失败了。

**执行的SQL：**
```sql
{final_sql if final_sql else '无'}
```

**错误原因：**
{execution_error or error}

**解决建议：**
1. 如果SQL包含CREATE等语句，系统不允许执行此类操作。建议使用子查询或CTE（WITH子句）代替临时表
2. 您可以直接编辑SQL并重试
3. 或者继续用自然语言描述您的需求，我会重新生成SQL"""
                
                # 确保返回的SQL不为空（从多个来源尝试获取）
                sql_to_return = final_sql
                if not sql_to_return:
                    sql_to_return = workflow_result.get("final_sql", "") or workflow_result.get("sql", "")
                if not sql_to_return:
                    # 如果还是没有，尝试从workflow_result的final_result中获取
                    final_result = workflow_result.get("final_result", {})
                    sql_to_return = final_result.get("final_sql", "") or final_result.get("sql", "")
                
                # 保存错误消息（确保SQL被正确保存）
                # 确保error_content不为None
                if not error_content or (isinstance(error_content, str) and error_content.strip() == ""):
                    error_content = f"""很抱歉，SQL执行失败了。

**执行的SQL：**
```sql
{final_sql if final_sql else '无'}
```

**错误原因：**
{execution_error or error}

**解决建议：**
1. 如果SQL包含CREATE等语句，系统不允许执行此类操作。建议使用子查询或CTE（WITH子句）代替临时表
2. 您可以直接编辑SQL并重试
3. 或者继续用自然语言描述您的需求，我会重新生成SQL"""
                
                logger.info(f"错误处理 - 最终error_content长度: {len(error_content) if error_content else 0}")
                
                assistant_message = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=error_content or "SQL执行失败，请查看错误信息",  # 双重保险
                    sql_statement=sql_to_return,  # 确保SQL被保存
                    error_message=execution_error or error,
                    tokens_used=0
                )
                db.add(assistant_message)
                session.updated_at = datetime.now()
                db.commit()
                db.refresh(assistant_message)
                
                # 即使有错误，也生成推荐问题（基于当前上下文、数据源和选择的表）
                recommended_questions = []
                try:
                    recommended_questions = await generate_dynamic_recommendations(
                        session_id=session_id,
                        current_question=request.question,
                        sql=sql_to_return,  # 使用确保不为空的SQL
                        data=None,  # 错误时没有数据
                        db=db,
                        current_user=current_user,
                        selected_tables=selected_tables  # 传递选择的表列表
                    )
                except Exception as e:
                    logger.warning(f"生成动态推荐问题失败: {e}，将返回空列表")
                
                # 记录日志，确保SQL被正确提取
                logger.info(f"错误处理：SQL={sql_to_return[:100] if sql_to_return else '空'}, 错误={execution_error or error}")
                
                return ResponseModel(
                    success=False,
                    message="SQL执行失败",
                    data={
                        "id": assistant_message.id,
                        "sql": sql_to_return,  # 确保SQL被返回
                        "error": execution_error or error,
                        "error_message": execution_error or error,
                        "can_retry": True,  # 允许重试
                        "can_continue_natural_language": True,  # 允许继续用自然语言提问
                        "data": [],
                        "data_total": 0,
                        "recommended_questions": recommended_questions  # 即使错误也提供推荐问题
                    }
                )
        
            # 13. 并行执行数据总结和推荐问题生成（优化性能）
            data_summary = None
            recommended_questions = []
        
            if data and len(data) > 0 and llm_client:
                # 并行执行数据总结和推荐问题生成
                try:
                    # 创建任务（协程需要先创建为任务才能并行执行）
                    data_summary_task = asyncio.create_task(generate_data_summary(
                        question=request.question,
                        sql=final_sql,
                        data=data,
                        llm_client=llm_client
                    ))
                    recommended_questions_task = asyncio.create_task(generate_dynamic_recommendations(
                        session_id=session_id,
                        current_question=request.question,
                        sql=final_sql,
                        data=data[:10] if data else None,
                        db=db,
                        current_user=current_user,
                        selected_tables=selected_tables,
                        llm_client=llm_client
                    ))
                    
                    # 并行等待两个任务完成
                    data_summary, recommended_questions = await asyncio.gather(
                        data_summary_task,
                        recommended_questions_task,
                        return_exceptions=True
                    )
                    
                    # 处理异常
                    if isinstance(data_summary, Exception):
                        logger.warning(f"生成数据总结失败: {data_summary}，不影响主流程")
                        data_summary = None
                    elif data_summary:
                        logger.info(f"生成数据总结成功，长度: {len(data_summary)}")
                    
                    if isinstance(recommended_questions, Exception):
                        logger.warning(f"生成动态推荐问题失败: {recommended_questions}，将返回空列表")
                        recommended_questions = []
                except Exception as e:
                    logger.warning(f"并行生成数据总结和推荐问题失败: {e}，不影响主流程")
                    # 降级：尝试单独生成推荐问题
                    try:
                        recommended_questions = await generate_dynamic_recommendations(
                            session_id=session_id,
                            current_question=request.question,
                            sql=final_sql,
                            data=data[:10] if data else None,
                            db=db,
                            current_user=current_user,
                            selected_tables=selected_tables,
                            llm_client=llm_client
                        )
                    except Exception as e2:
                        logger.warning(f"生成推荐问题失败: {e2}")
                        recommended_questions = []
        
            # 15. 保存AI回复（包含数据总结）
            # 如果有数据总结，将其合并到explanation中
            logger.info(f"准备保存AI回复: workflow_result存在={workflow_result is not None}, data长度={len(data) if data else 0}, error={error}, execution_error={execution_error}")
            
            explanation_content = workflow_result.get("explanation") if workflow_result else None
            logger.info(f"步骤1 - 初始explanation_content: {explanation_content}, data长度: {len(data) if data else 0}")
            
            if not explanation_content:
                # 如果没有explanation，生成一个默认的
                if data and len(data) > 0:
                    explanation_content = f"✅ SQL查询执行成功，返回 {len(data)} 条数据"
                else:
                    explanation_content = "✅ SQL查询执行成功，查询结果为空（0条数据）。这是正常情况，表示当前查询条件下没有匹配的数据。"
                logger.info(f"步骤2 - 生成默认explanation_content: {explanation_content}")
            
            if data_summary:
                explanation_content = f"{explanation_content}\n\n**数据分析总结：**\n{data_summary}"
                logger.info(f"步骤3 - 添加数据总结后的explanation_content长度: {len(explanation_content) if explanation_content else 0}")
            
            # 确保content不为None
            if not explanation_content or (isinstance(explanation_content, str) and explanation_content.strip() == ""):
                explanation_content = "SQL生成并执行成功"
                logger.info(f"步骤4 - 使用默认explanation_content: {explanation_content}")
            
            logger.info(f"步骤5 - 最终explanation_content: {explanation_content[:100] if explanation_content else 'None'}, 类型: {type(explanation_content)}")
            
            # 最终检查，确保content不为None
            final_content = explanation_content or "SQL生成并执行成功"
            logger.info(f"步骤6 - 创建ChatMessage前的final_content: {final_content[:100] if final_content else 'None'}")
            
            assistant_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=final_content,
                sql_statement=final_sql,
                chart_type=chart_config.get("type") if chart_config else None,
                chart_config=json.dumps(chart_config, ensure_ascii=False) if chart_config else None,
                query_result=json.dumps(data[:100], ensure_ascii=False) if data else None,  # 只保存前100条数据
                tokens_used=0  # 注意：token使用量统计功能待实现，需要从LLM客户端获取
            )
            db.add(assistant_message)
            
            # 15. 更新会话时间
            session.updated_at = datetime.now()
            
            # 16. 延迟生成对话标题（不阻塞主流程）
            # 查询会话中的用户消息数量（不包括刚创建的用户消息）
            user_messages_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
                ChatMessage.id != user_message.id  # 排除刚创建的用户消息
            ).count()
            
            # 如果这是第一条用户消息（user_messages_count == 0），或者标题是默认标题格式，则生成新标题
            # 使用后台任务，不阻塞响应
            if user_messages_count == 0 or (session.title and ("新对话" in session.title or session.title.startswith("对话 "))):
                # 保存 session_id 用于后台任务
                session_id_for_title = session.id
                question_for_title = request.question
                
                # 创建后台任务生成标题（不等待）
                async def generate_title_background():
                    try:
                        # 需要重新获取数据库会话（因为原会话可能已关闭）
                        from app.core.database import LocalSessionLocal
                        from app.models import ChatSession
                        db_session = LocalSessionLocal()
                        try:
                            # 重新从数据库加载 session 对象（重要：使用新的数据库会话）
                            session_to_update = db_session.query(ChatSession).filter(
                                ChatSession.id == session_id_for_title
                            ).first()
                            
                            if session_to_update:
                                await generate_session_title(session_to_update, question_for_title, db_session, llm_client)
                                db_session.commit()
                                logger.info(f"✅ 对话标题已更新并保存到数据库: {session_to_update.title}")
                            else:
                                logger.warning(f"未找到会话 {session_id_for_title}，无法更新标题")
                        finally:
                            db_session.close()
                    except Exception as e:
                        logger.warning(f"自动生成对话标题失败: {e}，保留原标题", exc_info=True)
                
                # 不等待，让它在后台执行
                asyncio.create_task(generate_title_background())
            
            db.commit()
            db.refresh(assistant_message)
            
            return ResponseModel(
                success=True,
                message="消息发送成功",
                data={
                    "id": assistant_message.id,
                    "sql": final_sql,
                    "explanation": explanation_content,  # 包含数据总结的完整解释
                    "data_summary": data_summary,  # 单独返回数据总结（可选）
                    "chart_type": chart_config.get("type") if chart_config else None,
                    "chart_config": chart_config,
                    "thinking_steps": workflow_result.get("thinking_steps", []),  # 返回思考步骤
                    "data": data[:100] if data else [],  # 只返回前100条
                    "data_total": len(data) if data else 0,
                    "tokens_used": 0,  # 注意：token使用量统计功能待实现
                    "model": model_config.model_name,
                    "retry_count": workflow_result.get("retry_count", 0),  # 重试次数
                    "recommended_questions": recommended_questions,  # 动态生成的推荐问题（基于当前会话上下文）
                    "question_rewrite": question_rewrite_info  # 问题改写信息（如果有）
                }
            )
        
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            # 使用%格式化避免f-string中的特殊字符问题
            error_msg = str(e)
            logger.error("发送消息失败: %s", error_msg, exc_info=True)
            # 确保错误消息安全
            safe_error_msg = error_msg.replace("{", "{{").replace("}", "}}")
            raise HTTPException(status_code=500, detail=f"发送消息失败: {safe_error_msg}")


def _generate_chart_config(chart_type: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            chart_type: 图表类型
            data: 数据列表
            
        Returns:
            ECharts配置JSON
        """
        if not data:
            return None
        
        # 获取数据列名
        columns = list(data[0].keys()) if data else []
        
        if chart_type == "bar":
            # 柱状图：第一列作为X轴，第二列作为Y轴
            x_data = [row[columns[0]] for row in data]
            y_data = [row[columns[1]] for row in data]
            return {
                "type": "bar",
                "xAxis": {"data": x_data},
                "series": [{
                    "name": columns[1] if len(columns) > 1 else "数值",
                    "data": y_data,
                    "type": "bar"
                }]
            }
        elif chart_type == "line":
            # 折线图
            x_data = [row[columns[0]] for row in data]
            y_data = [row[columns[1]] for row in data]
            return {
                "type": "line",
                "xAxis": {"data": x_data},
                "series": [{
                    "name": columns[1] if len(columns) > 1 else "数值",
                    "data": y_data,
                    "type": "line"
                }]
            }
        elif chart_type == "pie":
            # 饼图：第一列作为名称，第二列作为数值
            pie_data = [
                {"name": row[columns[0]], "value": row[columns[1]]}
                for row in data
            ]
            return {
                "type": "pie",
                "series": [{
                    "data": pie_data,
                    "type": "pie"
                }]
            }
        else:
            # 表格：返回原始数据
            return {
                "type": "table",
                "columns": columns,
                "data": data
            }


@router.get("/sessions/{session_id}/messages", response_model=ResponseModel)
async def get_messages(
    session_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取消息列表"""
    try:
        # 验证会话
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 查询消息
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        total = query.count()
        
        messages = query.order_by(ChatMessage.created_at).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        message_list = []
        for msg in messages:
            # 解析JSON字段
            chart_config = None
            if msg.chart_config:
                try:
                    chart_config = json.loads(msg.chart_config)
                except:
                    pass
            
            query_result = None
            if msg.query_result:
                try:
                    query_result = json.loads(msg.query_result)
                except:
                    pass
            
            message_list.append({
                "id": msg.id,
                "session_id": msg.session_id,
                "role": msg.role,
                "content": msg.content,
                "explanation": msg.content,  # 将content映射为explanation，因为content包含LLM生成的数据分析总结
                "sql": msg.sql_statement,
                "chart_type": msg.chart_type,
                "chart_config": chart_config,
                "data": query_result[:100] if query_result else None,  # 只返回前100条
                "data_total": len(query_result) if query_result else 0,
                "tokens_used": msg.tokens_used,
                "created_at": msg.created_at.isoformat()
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=message_list,
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")

