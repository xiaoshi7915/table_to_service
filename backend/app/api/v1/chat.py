"""
对话API
实现对话会话和消息管理
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from loguru import logger
from datetime import datetime
import json

from app.core.database import get_local_db
from app.core.security import get_current_active_user
from app.models import User, ChatSession, ChatMessage, DatabaseConfig, AIModelConfig, Terminology, SQLExample, BusinessKnowledge
from app.schemas import ResponseModel
from app.core.llm.factory import LLMFactory

router = APIRouter(prefix="/api/v1/chat", tags=["对话"])


# 请求模型
class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = None
    data_source_id: Optional[int] = None
    selected_tables: Optional[List[str]] = None  # 用户选择的表列表


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: str


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    question: str
    data_source_id: Optional[int] = None
    selected_tables: Optional[List[str]] = None  # 用户选择的表列表


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
        # 生成默认标题
        if not request.title:
            request.title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
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
        
        # 构建响应数据
        session_list = []
        for session in sessions:
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
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": session.id,
                "title": session.title,
                "data_source_id": session.data_source_id,
                "data_source_name": data_source_name,
                "selected_tables": selected_tables,
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
    """更新会话（重命名）"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session.title = request.title
        db.commit()
        db.refresh(session)
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={
                "id": session.id,
                "title": session.title
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
        
        # 4. 保存用户消息
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.question
        )
        db.add(user_message)
        db.commit()
        
        # 5. 获取AI模型配置
        model_config = db.query(AIModelConfig).filter(
            AIModelConfig.is_default == True,
            AIModelConfig.is_active == True
        ).first()
        
        if not model_config:
            raise HTTPException(status_code=400, detail="未配置默认AI模型")
        
        # 6. 创建LLM客户端
        llm_client = LLMFactory.create_client(model_config)
        
        # 7. 创建LangChain适配的LLM
        from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
        langchain_llm = LangChainLLMAdapter(llm_client)
        
        # 8. 创建RAG服务（使用LangChain版本）
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
        
        # 初始化嵌入服务
        embedding_service = None
        try:
            embedding_service = ChineseEmbeddingService()
            logger.info("使用中文嵌入模型（text2vec-base-chinese）")
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
                    logger.info("向量存储管理器初始化成功")
                else:
                    logger.warning("向量存储需要PostgreSQL数据库，当前配置不是PostgreSQL")
            except Exception as e:
                logger.warning(f"向量存储管理器初始化失败: {e}")
        
        # 创建检索器
        terminology_retriever = None
        sql_example_retriever = None
        knowledge_retriever = None
        
        if vector_manager:
            try:
                # 从数据库加载文档用于BM25检索
                terminologies = db.query(Terminology).all()
                sql_examples = db.query(SQLExample).all()
                knowledge_items = db.query(BusinessKnowledge).all()
                
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
                
                # 创建混合检索器
                if term_docs:
                    terminology_retriever = HybridRetriever(
                        vector_store=vector_manager.get_store("terminologies"),
                        documents=term_docs
                    )
                
                if sql_docs:
                    sql_example_retriever = HybridRetriever(
                        vector_store=vector_manager.get_store("sql_examples"),
                        documents=sql_docs
                    )
                
                if knowledge_docs:
                    knowledge_retriever = HybridRetriever(
                        vector_store=vector_manager.get_store("knowledge"),
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
        
        # 8. 创建RAG工作流
        rag_workflow = RAGWorkflow(
            llm=langchain_llm,
            terminology_retriever=terminology_retriever,
            sql_example_retriever=sql_example_retriever,
            knowledge_retriever=knowledge_retriever,
            max_retries=3
        )
        
        # 10. 运行工作流（传递选择的表列表）
        workflow_result = rag_workflow.run(
            question=request.question,
            db_config=db_config,
            selected_tables=selected_tables  # 使用从会话或请求中获取的表列表
        )
        
        # 10. 提取结果
        final_sql = workflow_result.get("sql", "")
        data = workflow_result.get("data", [])
        chart_config = workflow_result.get("chart_config")
        error = workflow_result.get("error")
        
        if error:
            logger.error(f"工作流执行失败: {error}")
            raise HTTPException(status_code=500, detail=f"SQL生成失败: {error}")
        
        # 11. 保存AI回复
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=workflow_result.get("explanation", "SQL生成并执行成功"),
            sql_statement=final_sql,
            chart_type=chart_config.get("type") if chart_config else None,
            chart_config=json.dumps(chart_config, ensure_ascii=False) if chart_config else None,
            query_result=json.dumps(data[:100], ensure_ascii=False) if data else None,  # 只保存前100条数据
            tokens_used=0  # TODO: 从工作流中获取token使用量
        )
        db.add(assistant_message)
        
        # 12. 更新会话时间
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(assistant_message)
        
        return ResponseModel(
            success=True,
            message="消息发送成功",
            data={
                "id": assistant_message.id,
                "sql": final_sql,
                "explanation": workflow_result.get("explanation", "SQL生成并执行成功"),
                "chart_type": chart_config.get("type") if chart_config else None,
                "chart_config": chart_config,
                "data": data[:100] if data else [],  # 只返回前100条
                "data_total": len(data) if data else 0,
                "tokens_used": 0,  # TODO: 从工作流中获取
                "model": model_config.model_name,
                "retry_count": workflow_result.get("retry_count", 0)  # 重试次数
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"发送消息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


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

