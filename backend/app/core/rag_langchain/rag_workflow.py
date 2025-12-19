"""
RAG工作流
使用LangGraph实现多步骤RAG流程，包含错误重试机制
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
try:
    # LangChain 1.x
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.documents import Document
    try:
        from langchain_core.retrievers import BaseRetriever
    except ImportError:
        from langchain.schema import BaseRetriever
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.base_language import BaseLanguageModel
    from langchain.schema import BaseRetriever, Document
from loguru import logger

from app.models import DatabaseConfig
from .schema_service import SchemaService
# 延迟导入rag_chain，避免循环依赖
# from .rag_chain import SQLRAGChain


class RAGState(TypedDict):
    """RAG状态"""
    # 输入
    question: str
    db_config: DatabaseConfig
    selected_tables: List[str]  # 用户选择的表
    
    # 中间状态
    schema_info: Dict[str, Any]  # Schema信息
    retrieved_contexts: Dict[str, List[Document]]  # 检索到的上下文
    merged_context: List[Document]  # 合并后的上下文
    prompt: str  # 构建的提示词
    
    # SQL生成和执行
    sql: str  # 生成的SQL
    sql_execution_result: Optional[Dict[str, Any]]  # SQL执行结果
    execution_error: Optional[str]  # 执行错误信息
    retry_count: int  # 重试次数
    
    # 最终结果
    final_sql: str  # 最终确定的SQL
    final_result: Dict[str, Any]  # 最终结果
    chart_config: Optional[Dict[str, Any]]  # 图表配置
    explanation: str  # 解释说明


class RAGWorkflow:
    """RAG工作流（使用LangGraph）"""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        terminology_retriever: BaseRetriever,
        sql_example_retriever: BaseRetriever,
        knowledge_retriever: BaseRetriever,
        max_retries: int = 3
    ):
        """
        初始化RAG工作流
        
        Args:
            llm: 大语言模型
            terminology_retriever: 术语检索器
            sql_example_retriever: SQL示例检索器
            knowledge_retriever: 知识库检索器
            max_retries: 最大重试次数
        """
        self.llm = llm
        self.terminology_retriever = terminology_retriever
        self.sql_example_retriever = sql_example_retriever
        self.knowledge_retriever = knowledge_retriever
        self.max_retries = max_retries
        
        # 构建工作流图
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(RAGState)
        
        # 添加节点
        workflow.add_node("load_schema", self._load_schema)
        workflow.add_node("retrieve_contexts", self._retrieve_contexts)
        workflow.add_node("merge_contexts", self._merge_contexts)
        workflow.add_node("build_prompt", self._build_prompt)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("handle_error", self._handle_error)
        workflow.add_node("generate_chart", self._generate_chart)
        
        # 设置入口
        workflow.set_entry_point("load_schema")
        
        # 添加边
        workflow.add_edge("load_schema", "retrieve_contexts")
        workflow.add_edge("retrieve_contexts", "merge_contexts")
        workflow.add_edge("merge_contexts", "build_prompt")
        workflow.add_edge("build_prompt", "generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        
        # 条件边：根据执行结果决定下一步
        workflow.add_conditional_edges(
            "execute_sql",
            self._should_retry,
            {
                "retry": "handle_error",
                "success": "generate_chart",
                "max_retries": END
            }
        )
        
        workflow.add_edge("handle_error", "generate_sql")  # 重试生成SQL
        workflow.add_edge("generate_chart", END)
        
        return workflow.compile()
    
    def _load_schema(self, state: RAGState) -> RAGState:
        """加载Schema信息"""
        try:
            schema_service = SchemaService(state["db_config"])
            state["schema_info"] = schema_service.get_table_schema(
                table_names=state.get("selected_tables"),
                include_sample_data=True,
                sample_rows=5
            )
            logger.info(f"加载Schema信息成功，包含 {len(state['schema_info']['tables'])} 个表")
        except Exception as e:
            logger.error(f"加载Schema信息失败: {e}", exc_info=True)
            state["schema_info"] = {"tables": [], "relationships": []}
        
        return state
    
    def _retrieve_contexts(self, state: RAGState) -> RAGState:
        """检索上下文"""
        question = state["question"]
        retrieved = {}
        
        try:
            # 检索术语
            # 尝试使用get_relevant_documents（LangChain 1.x）
            if hasattr(self.terminology_retriever, 'get_relevant_documents'):
                retrieved["terminologies"] = self.terminology_retriever.get_relevant_documents(question)
            else:
                retrieved["terminologies"] = self.terminology_retriever._get_relevant_documents(question)
            logger.info(f"检索到 {len(retrieved['terminologies'])} 个术语")
        except Exception as e:
            logger.warning(f"检索术语失败: {e}")
            retrieved["terminologies"] = []
        
        try:
            # 检索SQL示例
            if hasattr(self.sql_example_retriever, 'get_relevant_documents'):
                retrieved["sql_examples"] = self.sql_example_retriever.get_relevant_documents(question)
            else:
                retrieved["sql_examples"] = self.sql_example_retriever._get_relevant_documents(question)
            logger.info(f"检索到 {len(retrieved['sql_examples'])} 个SQL示例")
        except Exception as e:
            logger.warning(f"检索SQL示例失败: {e}")
            retrieved["sql_examples"] = []
        
        try:
            # 检索业务知识
            if hasattr(self.knowledge_retriever, 'get_relevant_documents'):
                retrieved["knowledge"] = self.knowledge_retriever.get_relevant_documents(question)
            else:
                retrieved["knowledge"] = self.knowledge_retriever._get_relevant_documents(question)
            logger.info(f"检索到 {len(retrieved['knowledge'])} 个知识条目")
        except Exception as e:
            logger.warning(f"检索业务知识失败: {e}")
            retrieved["knowledge"] = []
        
        state["retrieved_contexts"] = retrieved
        return state
    
    def _merge_contexts(self, state: RAGState) -> RAGState:
        """合并上下文"""
        merged = []
        retrieved = state["retrieved_contexts"]
        
        # 合并所有检索结果
        for category, docs in retrieved.items():
            merged.extend(docs)
        
        # 去重（基于文档内容）
        seen = set()
        unique_docs = []
        for doc in merged:
            content_hash = hash(doc.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)
        
        # 限制数量（避免提示词过长）
        state["merged_context"] = unique_docs[:20]  # 最多20个文档
        logger.info(f"合并后得到 {len(state['merged_context'])} 个唯一文档")
        
        return state
    
    def _build_prompt(self, state: RAGState) -> RAGState:
        """构建提示词"""
        schema_info = state["schema_info"]
        contexts = state["merged_context"]
        question = state["question"]
        db_type = state["db_config"].db_type or "mysql"
        
        # 构建Schema部分
        schema_text = self._format_schema(schema_info)
        
        # 构建上下文部分
        context_text = self._format_contexts(contexts)
        
        # 构建完整提示词
        prompt = f"""你是一个专业的SQL生成助手。请根据以下信息生成SQL查询语句。

## 数据库Schema信息
{schema_text}

## 相关上下文信息
{context_text}

## 用户问题
{question}

## 要求
1. 只生成SELECT查询语句，不要生成INSERT、UPDATE、DELETE等修改语句
2. 使用参数化查询防止SQL注入（使用:param_name格式）
3. 根据问题意图选择合适的聚合函数（SUM、COUNT、AVG、MAX、MIN等）
4. 合理使用GROUP BY、ORDER BY、LIMIT等子句
5. 生成的SQL要符合{db_type.upper()}语法规范
6. 如果问题中提到了业务术语，请使用对应的数据库字段名
7. 注意表之间的关联关系，使用正确的JOIN语句

请直接返回SQL语句，不要包含其他解释："""
        
        state["prompt"] = prompt
        return state
    
    def _generate_sql(self, state: RAGState) -> RAGState:
        """生成SQL"""
        try:
            # 使用LLM生成SQL
            prompt = state["prompt"]
            
            # 调用LLM（使用LangChain标准接口）
            try:
                if hasattr(self.llm, 'invoke'):
                    response = self.llm.invoke(prompt)
                    sql = response.content if hasattr(response, 'content') else str(response)
                elif hasattr(self.llm, '_generate'):
                    # 使用_generate方法
                    result = self.llm._generate([prompt])
                    if result.generations and result.generations[0]:
                        sql = result.generations[0][0].text
                    else:
                        sql = ""
                else:
                    # 降级方案：尝试直接调用
                    sql = str(self.llm(prompt))
                
                # 提取SQL（移除可能的Markdown格式）
                sql = self._extract_sql(sql)
                state["sql"] = sql
                
                logger.info(f"生成SQL: {sql[:100]}...")
            except Exception as e:
                logger.error(f"LLM调用失败: {e}", exc_info=True)
                # 如果LLM调用失败，尝试使用RAG链
                try:
                    from .rag_chain import SQLRAGChain
                    # 创建临时检索器（使用合并后的上下文）
                    try:
                        from langchain_core.retrievers import BaseRetriever
                    except ImportError:
                        try:
                            from langchain.retrievers import BaseRetriever
                        except ImportError:
                            from langchain.schema import BaseRetriever
                    class ContextRetriever(BaseRetriever):
                        def __init__(self, docs):
                            self.docs = docs
                        def _get_relevant_documents(self, query):
                            return self.docs
                    
                    temp_retriever = ContextRetriever(state["merged_context"])
                    rag_chain = SQLRAGChain(
                        llm=self.llm,
                        retriever=temp_retriever,
                        prompt_template=None  # 使用默认模板
                    )
                    result = rag_chain.generate_sql(
                        question=state["question"],
                        db_type=state["db_config"].db_type or "mysql"
                    )
                    sql = result.get("sql", "")
                    state["sql"] = sql
                except Exception as e2:
                    logger.error(f"RAG链生成SQL也失败: {e2}")
                    state["sql"] = ""
                    state["execution_error"] = f"生成SQL失败: {str(e)}"
        except Exception as e:
            logger.error(f"生成SQL失败: {e}", exc_info=True)
            state["sql"] = ""
            state["execution_error"] = f"生成SQL失败: {str(e)}"
        
        return state
    
    def _execute_sql(self, state: RAGState) -> RAGState:
        """执行SQL"""
        sql = state["sql"]
        db_config = state["db_config"]
        
        if not sql:
            state["execution_error"] = "SQL语句为空"
            state["sql_execution_result"] = None
            return state
        
        try:
            from app.core.db_factory import DatabaseConnectionFactory
            from sqlalchemy import text
            
            engine = DatabaseConnectionFactory.create_engine(db_config)
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                columns = result.keys()
                
                # 转换为字典列表
                data = []
                for row in rows[:1000]:  # 限制1000条
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        elif value is not None:
                            value = str(value)
                        row_dict[col] = value
                    data.append(row_dict)
            
            engine.dispose()
            
            state["sql_execution_result"] = {
                "success": True,
                "data": data,
                "row_count": len(data)
            }
            state["execution_error"] = None
            state["final_sql"] = sql
            
            logger.info(f"SQL执行成功，返回 {len(data)} 条数据")
            
        except Exception as e:
            error_msg = str(e)
            state["execution_error"] = error_msg
            state["sql_execution_result"] = {
                "success": False,
                "error": error_msg
            }
            state["retry_count"] = state.get("retry_count", 0) + 1
            
            logger.warning(f"SQL执行失败: {error_msg}")
        
        return state
    
    def _should_retry(self, state: RAGState) -> str:
        """判断是否应该重试"""
        if state["sql_execution_result"] and state["sql_execution_result"].get("success"):
            return "success"
        
        retry_count = state.get("retry_count", 0)
        if retry_count >= self.max_retries:
            return "max_retries"
        
        return "retry"
    
    def _handle_error(self, state: RAGState) -> RAGState:
        """处理错误，修改提示词重新生成SQL"""
        error_msg = state.get("execution_error", "")
        sql = state.get("sql", "")
        
        # 在提示词中添加错误信息
        error_prompt = f"""
之前的SQL执行失败，错误信息：{error_msg}

之前的SQL：{sql}

请根据错误信息修正SQL语句，确保：
1. SQL语法正确
2. 表名和字段名存在
3. 数据类型匹配
4. JOIN条件正确

修正后的SQL："""
        
        # 更新提示词
        state["prompt"] = state["prompt"] + "\n\n" + error_prompt
        
        logger.info(f"准备重试生成SQL（第 {state.get('retry_count', 0)} 次）")
        
        return state
    
    def _generate_chart(self, state: RAGState) -> RAGState:
        """生成图表配置"""
        data = state["sql_execution_result"].get("data", [])
        question = state["question"]
        
        if not data:
            state["chart_config"] = None
            state["explanation"] = "查询成功，但未返回数据"
            return state
        
        # 根据问题和数据特征生成图表配置
        chart_config = self._recommend_chart(question, data)
        state["chart_config"] = chart_config
        
        # 生成解释说明
        state["explanation"] = f"根据问题「{question}」成功生成并执行了SQL查询，返回 {len(data)} 条数据"
        
        state["final_result"] = {
            "sql": state["final_sql"],
            "data": data[:100],  # 只返回前100条
            "total_rows": len(data),
            "chart_config": chart_config
        }
        
        return state
    
    def _format_schema(self, schema_info: Dict[str, Any]) -> str:
        """格式化Schema信息"""
        tables = schema_info.get("tables", [])
        relationships = schema_info.get("relationships", [])
        
        schema_text = "### 表结构\n"
        for table in tables:
            schema_text += f"\n表名：{table['name']}\n"
            schema_text += "字段：\n"
            for col in table["columns"]:
                col_info = f"  - {col['name']} ({col['type']})"
                if col.get("primary_key"):
                    col_info += " [主键]"
                if col.get("comment"):
                    col_info += f" - {col['comment']}"
                schema_text += col_info + "\n"
            
            # 添加样例数据
            if table.get("sample_data"):
                schema_text += "\n样例数据：\n"
                for i, sample in enumerate(table["sample_data"][:3], 1):
                    schema_text += f"  示例{i}: {sample}\n"
        
        if relationships:
            schema_text += "\n### 表关联关系\n"
            for rel in relationships:
                schema_text += f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}\n"
        
        return schema_text
    
    def _format_contexts(self, contexts: List[Document]) -> str:
        """格式化上下文信息"""
        if not contexts:
            return "无相关上下文"
        
        context_text = ""
        for i, doc in enumerate(contexts[:10], 1):  # 最多10个
            context_text += f"\n上下文{i}:\n{doc.page_content}\n"
            if doc.metadata:
                context_text += f"来源: {doc.metadata}\n"
        
        return context_text
    
    def _extract_sql(self, text: str) -> str:
        """从文本中提取SQL"""
        import re
        
        # 移除Markdown代码块
        text = re.sub(r'```(?:sql)?\s*\n?(.*?)\n?```', r'\1', text, flags=re.DOTALL)
        
        # 提取SELECT语句
        match = re.search(r'(SELECT\s+.*?)(?:;|$)', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 清理空白
        return ' '.join(text.split()).strip()
    
    def _recommend_chart(self, question: str, data: List[Dict]) -> Dict[str, Any]:
        """推荐图表类型"""
        question_lower = question.lower()
        
        if not data:
            return {"type": "table"}
        
        columns = list(data[0].keys())
        
        # 根据问题关键词判断
        if any(kw in question_lower for kw in ["趋势", "变化", "增长", "下降", "时间"]):
            return {
                "type": "line",
                "xAxis": {"data": [str(row.get(columns[0], "")) for row in data[:20]]},
                "series": [{
                    "name": columns[1] if len(columns) > 1 else "数值",
                    "data": [row.get(columns[1], 0) if len(columns) > 1 else 0 for row in data[:20]],
                    "type": "line"
                }]
            }
        
        if any(kw in question_lower for kw in ["占比", "比例", "百分比", "分布"]):
            return {
                "type": "pie",
                "series": [{
                    "data": [
                        {"name": str(row.get(columns[0], "")), "value": row.get(columns[1], 0)}
                        for row in data[:20]
                    ],
                    "type": "pie"
                }]
            }
        
        # 默认柱状图
        return {
            "type": "bar",
            "xAxis": {"data": [str(row.get(columns[0], "")) for row in data[:20]]},
            "series": [{
                "name": columns[1] if len(columns) > 1 else "数值",
                "data": [row.get(columns[1], 0) if len(columns) > 1 else 0 for row in data[:20]],
                "type": "bar"
            }]
        }
    
    def run(
        self,
        question: str,
        db_config: DatabaseConfig,
        selected_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            question: 用户问题
            db_config: 数据库配置
            selected_tables: 选择的表列表
            
        Returns:
            最终结果
        """
        initial_state = RAGState(
            question=question,
            db_config=db_config,
            selected_tables=selected_tables or [],
            schema_info={},
            retrieved_contexts={},
            merged_context=[],
            prompt="",
            sql="",
            sql_execution_result=None,
            execution_error=None,
            retry_count=0,
            final_sql="",
            final_result={},
            chart_config=None,
            explanation=""
        )
        
        try:
            result = self.workflow.invoke(initial_state)
            
            # 提取最终结果
            final_result = result.get("final_result", {})
            if not final_result:
                # 如果final_result为空，从状态中提取
                final_result = {
                    "sql": result.get("final_sql", result.get("sql", "")),
                    "data": result.get("sql_execution_result", {}).get("data", []) if result.get("sql_execution_result") and result.get("sql_execution_result").get("success") else [],
                    "chart_config": result.get("chart_config"),
                    "explanation": result.get("explanation", ""),
                    "retry_count": result.get("retry_count", 0),
                    "error": result.get("execution_error")
                }
            
            return final_result
        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            return {
                "sql": "",
                "data": [],
                "error": str(e),
                "chart_config": None,
                "explanation": f"工作流执行失败: {str(e)}",
                "retry_count": 0
            }

