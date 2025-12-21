"""
RAG工作流
使用LangGraph实现多步骤RAG流程，包含错误重试机制
"""
import re
import asyncio
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
    thinking_steps: List[Dict[str, Any]]  # 思考步骤记录
    
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
        workflow.add_node("load_schema_and_retrieve", self._load_schema_and_retrieve_parallel)
        workflow.add_node("merge_contexts", self._merge_contexts)
        workflow.add_node("build_prompt", self._build_prompt)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("handle_error", self._handle_error)
        workflow.add_node("generate_chart", self._generate_chart)
        
        # 设置入口
        workflow.set_entry_point("load_schema_and_retrieve")
        
        # 添加边
        workflow.add_edge("load_schema_and_retrieve", "merge_contexts")
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
    
    def _load_schema_and_retrieve_parallel(self, state: RAGState) -> RAGState:
        """并行加载Schema信息和检索上下文"""
        question = state["question"]
        
        # 记录思考步骤
        if "thinking_steps" not in state:
            state["thinking_steps"] = []
        state["thinking_steps"].append({
            "step": "加载数据库Schema和检索相关知识",
            "status": "进行中",
            "message": "正在分析数据库表结构和检索相关术语、SQL示例..."
        })
        
        def load_schema():
            """加载Schema信息（同步函数）"""
            try:
                schema_service = SchemaService(
                    state["db_config"],
                    enable_cache=True,  # 启用缓存
                    cache_ttl=3600  # 1小时
                )
                return schema_service.get_table_schema(
                    table_names=state.get("selected_tables"),
                    include_sample_data=True,
                    sample_rows=5
                )
            except Exception as e:
                logger.error(f"加载Schema信息失败: {e}", exc_info=True)
                return {"tables": [], "relationships": []}
        
        def retrieve_terminologies():
            """检索术语"""
            try:
                if self.terminology_retriever is None:
                    logger.debug("术语检索器未初始化，跳过检索")
                    return []
                if hasattr(self.terminology_retriever, 'get_relevant_documents'):
                    docs = self.terminology_retriever.get_relevant_documents(question)
                    logger.debug(f"术语检索返回 {len(docs)} 个文档")
                    return docs
                else:
                    docs = self.terminology_retriever._get_relevant_documents(question)
                    logger.debug(f"术语检索返回 {len(docs)} 个文档")
                    return docs
            except Exception as e:
                logger.warning(f"检索术语失败: {e}", exc_info=True)
                return []
        
        def retrieve_sql_examples():
            """检索SQL示例"""
            try:
                if self.sql_example_retriever is None:
                    logger.debug("SQL示例检索器未初始化，跳过检索")
                    return []
                if hasattr(self.sql_example_retriever, 'get_relevant_documents'):
                    docs = self.sql_example_retriever.get_relevant_documents(question)
                    logger.debug(f"SQL示例检索返回 {len(docs)} 个文档")
                    return docs
                else:
                    docs = self.sql_example_retriever._get_relevant_documents(question)
                    logger.debug(f"SQL示例检索返回 {len(docs)} 个文档")
                    return docs
            except Exception as e:
                logger.warning(f"检索SQL示例失败: {e}", exc_info=True)
                return []
        
        def retrieve_knowledge():
            """检索业务知识"""
            try:
                if self.knowledge_retriever is None:
                    logger.debug("知识库检索器未初始化，跳过检索")
                    return []
                if hasattr(self.knowledge_retriever, 'get_relevant_documents'):
                    docs = self.knowledge_retriever.get_relevant_documents(question)
                    logger.debug(f"知识库检索返回 {len(docs)} 个文档")
                    return docs
                else:
                    docs = self.knowledge_retriever._get_relevant_documents(question)
                    logger.debug(f"知识库检索返回 {len(docs)} 个文档")
                    return docs
            except Exception as e:
                logger.warning(f"检索业务知识失败: {e}", exc_info=True)
                return []
        
        # 并行执行所有操作
        try:
            # 使用线程池并行执行（因为这些操作主要是I/O密集型）
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                schema_future = executor.submit(load_schema)
                term_future = executor.submit(retrieve_terminologies)
                sql_future = executor.submit(retrieve_sql_examples)
                knowledge_future = executor.submit(retrieve_knowledge)
                
                # 等待所有任务完成
                schema_info = schema_future.result()
                terminologies = term_future.result()
                sql_examples = sql_future.result()
                knowledge = knowledge_future.result()
            
            state["schema_info"] = schema_info
            state["retrieved_contexts"] = {
                "terminologies": terminologies,
                "sql_examples": sql_examples,
                "knowledge": knowledge
            }
            
            logger.info(f"并行加载完成：Schema包含 {len(schema_info['tables'])} 个表，"
                       f"检索到 {len(terminologies)} 个术语，{len(sql_examples)} 个SQL示例，{len(knowledge)} 个知识条目")
            
            # 更新思考步骤
            state["thinking_steps"][-1]["status"] = "完成"
            state["thinking_steps"][-1]["message"] = f"已加载 {len(schema_info['tables'])} 个表结构，检索到 {len(terminologies)} 个术语、{len(sql_examples)} 个SQL示例、{len(knowledge)} 个知识条目"
        except Exception as e:
            logger.error(f"并行加载失败: {e}", exc_info=True)
            # 降级到串行执行
            state["schema_info"] = load_schema()
            state["retrieved_contexts"] = {
                "terminologies": retrieve_terminologies(),
                "sql_examples": retrieve_sql_examples(),
                "knowledge": retrieve_knowledge()
            }
            # 更新思考步骤
            state["thinking_steps"][-1]["status"] = "完成"
            state["thinking_steps"][-1]["message"] = "Schema加载完成（降级到串行模式）"
        
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
1. **只生成SELECT查询语句**，绝对不要生成INSERT、UPDATE、DELETE、CREATE、DROP、ALTER等任何修改或建表语句
2. **禁止使用临时表**：如果查询逻辑复杂，请使用子查询、CTE（WITH子句）或JOIN来实现，不要创建临时表
3. 使用参数化查询防止SQL注入（使用:param_name格式）
4. 根据问题意图选择合适的聚合函数（SUM、COUNT、AVG、MAX、MIN等）
5. 合理使用GROUP BY、ORDER BY、LIMIT等子句
6. 生成的SQL要符合{db_type.upper()}语法规范
7. 如果问题中提到了业务术语，请使用对应的数据库字段名
8. 注意表之间的关联关系，使用正确的JOIN语句

**重要：如果查询需要复杂逻辑，请使用子查询或CTE，不要使用CREATE TABLE语句。**

请直接返回SQL语句，不要包含其他解释："""
        
        state["prompt"] = prompt
        return state
    
    def _generate_sql(self, state: RAGState) -> RAGState:
        """生成SQL"""
        # 记录思考步骤
        if "thinking_steps" not in state:
            state["thinking_steps"] = []
        retry_count = state.get("retry_count", 0)
        if retry_count > 0:
            state["thinking_steps"].append({
                "step": f"重新生成SQL（第{retry_count}次重试）",
                "status": "进行中",
                "message": "根据错误信息重新分析问题并生成SQL..."
            })
        else:
            state["thinking_steps"].append({
                "step": "生成SQL查询",
                "status": "进行中",
                "message": "基于数据库Schema和相关知识生成SQL语句..."
            })
        
        try:
            # 使用LLM生成SQL
            prompt = state["prompt"]
            
            # 调用LLM（使用LangChain标准接口）
            try:
                if hasattr(self.llm, 'invoke'):
                    response = self.llm.invoke(prompt)
                    sql_raw = response.content if hasattr(response, 'content') else str(response)
                    
                    # 检查是否是错误消息
                    if sql_raw and ("LLM调用失败" in sql_raw or "调用失败" in sql_raw or "LLM客户端未初始化" in sql_raw):
                        logger.error("LLM返回错误消息: %s", sql_raw[:200])
                        raise ValueError(f"LLM调用失败: {sql_raw}")
                elif hasattr(self.llm, '_generate'):
                    # 使用_generate方法
                    result = self.llm._generate([prompt])
                    if result.generations and result.generations[0]:
                        sql_raw = result.generations[0][0].text
                        # 检查是否是错误消息
                        if sql_raw and ("生成失败" in sql_raw or "LLM调用失败" in sql_raw):
                            raise ValueError(f"LLM生成失败: {sql_raw}")
                    else:
                        sql_raw = ""
                else:
                    # 降级方案：尝试直接调用
                    sql_raw = str(self.llm(prompt))
                    # 检查是否是错误消息
                    if sql_raw and ("调用失败" in sql_raw or "LLM" in sql_raw):
                        raise ValueError(f"LLM调用失败: {sql_raw}")
                
                # 提取SQL（移除可能的Markdown格式）
                sql = self._extract_sql(sql_raw)
                
                # 修复缺少WITH关键字的CTE
                sql = self._fix_cte_sql(sql)
                
                # 检查SQL是否包含不允许的语句（CREATE、DROP等）
                # 使用正则表达式匹配单词边界，避免误判字段名（如created_at）
                import re
                sql_upper = sql.upper().strip()
                forbidden_keywords = ["CREATE", "DROP", "ALTER", "INSERT", "UPDATE", "DELETE", "TRUNCATE"]
                
                # 使用正则表达式匹配单词边界，确保只匹配SQL关键字，不匹配字段名
                contains_forbidden = False
                for keyword in forbidden_keywords:
                    # 使用\b匹配单词边界，确保是完整的SQL关键字
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, sql_upper):
                        contains_forbidden = True
                        logger.warning(f"检测到SQL关键字 {keyword}，SQL预览: {sql[:200]}...")
                        break
                
                if contains_forbidden:
                    # 如果包含不允许的语句，标记为需要用户手动处理
                    logger.warning(f"生成的SQL包含不允许的语句: {sql[:200]}...")
                    state["sql"] = sql  # 保存完整SQL
                    state["contains_complex_sql"] = True  # 标记为复杂SQL
                    state["execution_error"] = None  # 不是执行错误，而是需要用户手动处理
                    state["sql_execution_result"] = None
                    return state
                
                state["sql"] = sql
                state["contains_complex_sql"] = False
                
                # 更新思考步骤
                state["thinking_steps"][-1]["status"] = "完成"
                state["thinking_steps"][-1]["message"] = f"SQL生成成功: {sql[:50]}..."
                
                logger.info(f"生成SQL: {sql[:100]}...")
            except Exception as e:
                logger.error(f"LLM调用失败: {e}", exc_info=True)
                # 如果LLM调用失败，尝试使用RAG链
                try:
                    try:
                        from .rag_chain import SQLRAGChain
                    except ImportError as import_err:
                        logger.error(f"无法导入RAG链模块: {import_err}", exc_info=True)
                        raise ValueError(f"RAG链模块不可用: {str(import_err)}")
                    # 创建临时检索器（使用合并后的上下文）
                    try:
                        from langchain_core.retrievers import BaseRetriever
                    except ImportError:
                        from langchain.schema import BaseRetriever
                    class ContextRetriever(BaseRetriever):
                        def __init__(self, docs):
                            self.docs = docs
                        def _get_relevant_documents(self, query):
                            return self.docs
                        def get_relevant_documents(self, query):
                            return self.docs
                        async def aget_relevant_documents(self, query):
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
                    # 使用原始LLM错误，而不是RAG链错误
                    error_msg = f"生成SQL失败: {str(e)}"
                    state["execution_error"] = error_msg
                    # 设置sql_execution_result，确保_should_retry能正确判断
                    state["sql_execution_result"] = {
                        "success": False,
                        "error": error_msg
                    }
                    # 增加重试计数，但不再重试（因为已经达到最大重试次数或LLM调用失败）
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    # 不再重试，直接返回失败状态
                    return state
        except Exception as e:
            logger.error(f"生成SQL失败: {e}", exc_info=True)
            # 设置错误状态，确保_should_retry能正确判断
            error_msg = f"生成SQL失败: {str(e)}"
            state["execution_error"] = error_msg
            state["sql_execution_result"] = {
                "success": False,
                "error": error_msg
            }
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["sql"] = ""
        
        return state
    
    def _execute_sql(self, state: RAGState) -> RAGState:
        """执行SQL"""
        # 记录思考步骤
        if "thinking_steps" not in state:
            state["thinking_steps"] = []
        state["thinking_steps"].append({
            "step": "执行SQL查询",
            "status": "进行中",
            "message": "正在执行SQL并获取查询结果..."
        })
        
        sql = state["sql"]
        db_config = state["db_config"]
        
        # 如果SQL包含复杂逻辑（如CREATE语句），不执行，直接返回
        if state.get("contains_complex_sql", False):
            state["execution_error"] = None  # 不是错误，而是需要用户手动处理
            state["sql_execution_result"] = {
                "success": False,
                "error": "complex_sql_requires_manual_handling",
                "sql": sql
            }
            state["final_sql"] = sql
            state["thinking_steps"][-1]["status"] = "跳过"
            state["thinking_steps"][-1]["message"] = "SQL包含复杂逻辑，需要手动处理"
            logger.info("SQL包含复杂逻辑（如CREATE语句），跳过执行，返回SQL给用户")
            return state
        
        if not sql:
            error_msg = "SQL语句为空，LLM调用可能失败"
            state["execution_error"] = error_msg
            state["sql_execution_result"] = {
                "success": False,
                "error": error_msg
            }
            state["thinking_steps"][-1]["status"] = "失败"
            state["thinking_steps"][-1]["message"] = error_msg
            # 增加重试计数，但不再重试（因为LLM调用失败）
            state["retry_count"] = state.get("retry_count", 0) + 1
            return state
        
        try:
            # 使用SQL执行服务
            from .sql_executor import SQLExecutor
            
            executor = SQLExecutor(
                db_config=db_config,
                timeout=30,
                max_rows=1000,
                enable_cache=True,  # 启用缓存
                cache_ttl=600  # 10分钟
            )
            
            result = executor.execute(sql)
            
            if result["success"]:
                state["sql_execution_result"] = {
                    "success": True,
                    "data": result["data"],
                    "row_count": result["row_count"],
                    "total_rows": result.get("total_rows", result["row_count"]),
                    "columns": result.get("columns", []),
                    "execution_time": result.get("execution_time", 0)
                }
                state["execution_error"] = None
                state["final_sql"] = sql
                
                logger.info(f"SQL执行成功，返回 {result['row_count']} 条数据，耗时 {result.get('execution_time', 0):.2f}秒")
            else:
                error_msg = result.get("error", "SQL执行失败")
                state["execution_error"] = error_msg
                state["sql_execution_result"] = {
                    "success": False,
                    "error": error_msg
                }
                # 更新思考步骤
                if "thinking_steps" in state and len(state["thinking_steps"]) > 0:
                    state["thinking_steps"][-1]["status"] = "失败"
                    state["thinking_steps"][-1]["message"] = f"SQL执行失败: {error_msg[:50]}..."
                # 确保SQL被保存到final_sql，即使执行失败
                if sql and not state.get("final_sql"):
                    state["final_sql"] = sql
                state["retry_count"] = state.get("retry_count", 0) + 1
                
                logger.warning(f"SQL执行失败: {error_msg}")
            
        except Exception as e:
            error_msg = str(e)
            state["execution_error"] = error_msg
            state["sql_execution_result"] = {
                "success": False,
                "error": error_msg
            }
            # 确保SQL被保存到final_sql，即使执行失败
            if sql and not state.get("final_sql"):
                state["final_sql"] = sql
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
        sql = state.get("final_sql", "")
        
        if not data:
            state["chart_config"] = None
            state["explanation"] = "查询成功，但未返回数据"
            return state
        
        # 使用图表服务生成配置
        from .chart_service import ChartService
        chart_service = ChartService()
        chart_config = chart_service.generate_chart_config(question, data, sql)
        state["chart_config"] = chart_config
        
        # 生成解释说明
        chart_type = chart_config.get("type", "table")
        state["explanation"] = f"根据问题「{question}」成功生成并执行了SQL查询，返回 {len(data)} 条数据，已生成{chart_type}图表"
        
        state["final_result"] = {
            "sql": state["final_sql"],
            "data": data[:100],  # 只返回前100条
            "total_rows": len(data),
            "chart_config": chart_config,
            "chart_type": chart_type
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
        
        
        # 移除Markdown代码块（保留内容）
        original_text = text
        text = re.sub(r'```(?:sql)?\s*\n?(.*?)\n?```', r'\1', text, flags=re.DOTALL)
        
        

        # 检查是否包含CREATE等语句
        text_upper = text.upper()
        if "CREATE" in text_upper or "DROP" in text_upper or "ALTER" in text_upper:
            # 如果包含CREATE等语句，返回完整SQL（不执行，只提供给用户）
            # 尝试提取所有SQL语句（包括CREATE和SELECT）
            sql_parts = []
            # 提取CREATE语句
            create_match = re.search(r'(CREATE\s+.*?)(?:;|$)', text, re.DOTALL | re.IGNORECASE)
            if create_match:
                sql_parts.append(create_match.group(1).strip())
            # 提取WITH CTE语句（优先）
            with_match = re.search(r'(WITH\s+\w+\s+AS\s*\([^)]+\)\s+SELECT\s+.*?)(?:;|$)', text, re.DOTALL | re.IGNORECASE)
            if with_match:
                sql_parts.append(with_match.group(1).strip())
            else:
                # 提取SELECT语句
                select_match = re.search(r'(SELECT\s+.*?)(?:;|$)', text, re.DOTALL | re.IGNORECASE)
                if select_match:
                    sql_parts.append(select_match.group(1).strip())
            
            if sql_parts:
                return "\n\n".join(sql_parts)
            # 如果没有找到，返回原始文本
            return ' '.join(text.split()).strip()

        # **关键修复**：优先提取WITH CTE语句（使用更精确的正则，支持多行和嵌套括号）
        # 匹配模式：WITH 表名 AS ( ... ) SELECT ...
        # 使用递归或平衡括号匹配
        with_pattern = r'(WITH\s+\w+\s+AS\s*\((?:[^()]|\([^()]*\))*\)\s+SELECT\s+.*?)(?:;|$)'
        with_match = re.search(with_pattern, text, re.DOTALL | re.IGNORECASE)
        if with_match:
            extracted = with_match.group(1).strip()
            
            return extracted
        
        # 如果上面的正则没匹配到（可能括号嵌套复杂），尝试手动解析
        if "WITH" in text_upper and "AS" in text_upper:
            # 查找WITH关键字的位置
            with_pos = text_upper.find("WITH")
            if with_pos >= 0:
                # 从WITH开始提取，直到遇到分号或文本结束
                # 找到最后一个SELECT后的内容
                remaining = text[with_pos:]
                # 查找分号位置
                semicolon_pos = remaining.find(';')
                if semicolon_pos > 0:
                    extracted = remaining[:semicolon_pos].strip()
                else:
                    extracted = remaining.strip()
                
                
                
                if extracted and "WITH" in extracted.upper():
                    return extracted
        
        # 提取SELECT语句（正常情况）- 但可能不完整（如果包含CTE）
        # 尝试匹配以括号开头的SELECT（可能是CTE的一部分）
        if text.strip().startswith('('):
            # 可能是CTE格式，尝试提取完整内容直到遇到分号或结尾
            # 查找从第一个SELECT到最后一个SELECT的完整内容
            select_pattern = r'((?:\([^)]*\)|SELECT[^;]*)+)(?:;|$)'
            match = re.search(select_pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # 检查是否包含两个SELECT（CTE模式）
                if extracted.upper().count('SELECT') >= 2:
                    return extracted
        else:
            # 普通SELECT提取（使用贪婪匹配，确保获取完整语句）
            # 注意：这里使用贪婪匹配可能有问题，但如果没有WITH，应该只有一个SELECT
            match = re.search(r'(SELECT\s+.*?)(?:;|$)', text, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                
                return extracted

        # 清理空白
        result = ' '.join(text.split()).strip()
        
        return result
    
    def _fix_cte_sql(self, sql: str) -> str:
        """修复缺少WITH关键字的CTE SQL"""
        if not sql:
            return sql
        
        sql_upper = sql.upper().strip()
        
        # 如果已经有WITH关键字，直接返回
        if sql_upper.startswith('WITH'):
            return sql
        
        # 检测模式1：以括号包围的SELECT开头，后面跟着另一个SELECT
        if sql.strip().startswith('('):
            # 手动解析括号
            paren_count = 0
            cte_end = -1
            for i, char in enumerate(sql):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        cte_end = i + 1
                        break
            
            if cte_end > 0:
                # 检查后面是否跟着SELECT
                remaining = sql[cte_end:].strip()
                
                if remaining.upper().startswith('SELECT'):
                    # 提取CTE部分
                    cte_query = sql[1:cte_end-1].strip()  # 移除外层括号
                    
                    # 从主查询中提取CTE名称
                    from_match = re.search(r'FROM\s+(\w+)', remaining, re.IGNORECASE)
                    
                    if from_match:
                        cte_name = from_match.group(1)
                        
                        # 重构SQL，添加WITH关键字
                        fixed_sql = f"WITH {cte_name} AS (\n    {cte_query}\n)\n{remaining}"
                        logger.info(f"检测到缺少WITH关键字的CTE（模式1），已自动修复: {cte_name}")
                        return fixed_sql
        
        # 检测模式2：以SELECT开头，后面跟着 `),` 和另一个CTE定义
        # 模式：SELECT ... FROM ... [WHERE ...] [GROUP BY ...]\n),\ncte_name AS (\nSELECT ...
        if sql_upper.startswith('SELECT'):
            # 查找 `),\n` 或 `),\n` 后面跟着 `cte_name AS (`
            # 这个模式表示有多个CTE，但缺少WITH关键字
            # 匹配：SELECT ... [各种子句] ... ), cte_name AS (
            pattern = r'^(SELECT\s+.*?)\s*\),\s*(\w+)\s+AS\s*\('
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            
            if match:
                # 找到第一个CTE的SELECT部分（到 `),` 之前）
                first_cte_query = match.group(1).strip()
                second_cte_name = match.group(2)
                
                # 查找第一个CTE的名称（从主查询的FROM子句中）
                # 查找所有 `FROM table_name` 的模式，取最后一个（应该是主查询中的第一个CTE）
                all_from_matches = list(re.finditer(r'FROM\s+(\w+)', sql, re.IGNORECASE))
                if len(all_from_matches) >= 2:
                    # 第一个FROM是第一个CTE中的，第二个FROM是第二个CTE中的
                    # 第三个FROM是主查询中的，引用第一个CTE
                    main_from_match = all_from_matches[-1]  # 最后一个FROM是主查询
                    first_cte_name = main_from_match.group(1)
                    
                    # 提取第二个CTE及其后的主查询
                    # 找到第二个CTE的开始位置（`AS (` 之后）
                    second_cte_start = match.end()
                    # 找到第二个CTE的结束位置（对应的右括号）
                    paren_count = 1
                    second_cte_end = second_cte_start
                    for i in range(second_cte_start, len(sql)):
                        if sql[i] == '(':
                            paren_count += 1
                        elif sql[i] == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                second_cte_end = i + 1
                                break
                    
                    # 提取第二个CTE的内容
                    second_cte_query = sql[second_cte_start:second_cte_end-1].strip()
                    
                    # 提取主查询（第二个CTE之后的部分）
                    main_query = sql[second_cte_end:].strip()
                    
                    # 重构SQL，添加WITH关键字
                    fixed_sql = f"WITH {first_cte_name} AS (\n    {first_cte_query}\n),\n{second_cte_name} AS (\n    {second_cte_query}\n)\n{main_query}"
                    logger.info(f"检测到缺少WITH关键字的多个CTE（模式2），已自动修复: {first_cte_name}, {second_cte_name}")
                    return fixed_sql
        
        return sql
    
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
            thinking_steps=[],
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
                # 确保SQL被正确提取（优先使用final_sql，如果没有则使用sql）
                extracted_sql = result.get("final_sql") or result.get("sql", "")
                final_result = {
                    "sql": extracted_sql,
                    "final_sql": extracted_sql,  # 确保final_sql字段存在
                    "data": result.get("sql_execution_result", {}).get("data", []) if result.get("sql_execution_result") and result.get("sql_execution_result").get("success") else [],
                    "chart_config": result.get("chart_config"),
                    "explanation": result.get("explanation", ""),
                    "retry_count": result.get("retry_count", 0),
                    "error": result.get("execution_error"),
                    "contains_complex_sql": result.get("contains_complex_sql", False),  # 添加复杂SQL标记
                    "thinking_steps": result.get("thinking_steps", [])  # 添加思考步骤
                }
            
            # 确保返回contains_complex_sql字段和final_sql字段
            if "contains_complex_sql" not in final_result:
                final_result["contains_complex_sql"] = result.get("contains_complex_sql", False)
            
            # 确保thinking_steps字段存在
            if "thinking_steps" not in final_result:
                final_result["thinking_steps"] = result.get("thinking_steps", [])
            
            # 确保final_sql字段存在（即使执行失败也要返回SQL）
            if "final_sql" not in final_result or not final_result.get("final_sql"):
                final_result["final_sql"] = result.get("final_sql") or result.get("sql", "")
            
            # 确保sql字段也存在（向后兼容）
            if "sql" not in final_result or not final_result.get("sql"):
                final_result["sql"] = final_result.get("final_sql", "")
            
            logger.info(f"工作流返回结果：SQL={final_result.get('final_sql', '')[:100] if final_result.get('final_sql') else '空'}, 错误={final_result.get('error', '无')}")
            
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

