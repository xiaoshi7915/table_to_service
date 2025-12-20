"""
SQL生成服务
调用LLM生成SQL，并进行验证和优化
支持缓存机制以提升性能
"""
import re
import json
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.llm.base import BaseLLMClient
from app.core.rag.prompt_builder import PromptBuilder
from app.core.rag.schema_loader import SchemaLoader
from app.core.cache import get_cache_service
from app.models import DatabaseConfig

# #region agent log
DEBUG_LOG_PATH = "/opt/table_to_service/.cursor/debug.log"
def _debug_log(location, message, data, hypothesis_id=None):
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            import time
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000)
            }
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion


class SQLGenerator:
    """SQL生成器"""
    
    # 危险的SQL关键字（禁止生成）
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", 
        "INSERT", "UPDATE", "GRANT", "REVOKE", "EXEC", 
        "EXECUTE", "CALL", "MERGE"
    ]
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        prompt_builder: PromptBuilder,
        schema_loader: Optional[SchemaLoader] = None,
        enable_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        初始化SQL生成器
        
        Args:
            llm_client: LLM客户端
            prompt_builder: 提示词构建器
            schema_loader: Schema加载器（可选）
            enable_cache: 是否启用缓存（默认True）
            cache_ttl: 缓存过期时间（秒，默认1小时）
        """
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.schema_loader = schema_loader
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.cache_service = get_cache_service() if enable_cache else None
    
    async def generate_sql(
        self,
        question: str,
        db_config: DatabaseConfig,
        context: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        生成SQL语句
        
        Args:
            question: 用户问题
            db_config: 数据库配置
            context: 对话上下文（可选）
            max_retries: 最大重试次数
            
        Returns:
            包含SQL和相关信息的字典：{
                "sql": "SQL语句",
                "explanation": "SQL说明",
                "chart_type": "推荐的图表类型",
                "tokens_used": token使用量
            }
        """
        # 检查缓存（如果启用）
        if self.enable_cache and self.cache_service:
            cache_key = self.cache_service._generate_key(
                "sql_generation",
                question=question,
                db_config_id=db_config.id,
                db_type=db_config.db_type or "mysql",
                context_hash=hash(str(context)) if context else None
            )
            cached_result = self.cache_service.get(cache_key)
            if cached_result:
                logger.info(f"从缓存获取SQL生成结果: {question[:50]}...")
                return cached_result
        
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                # 1. 加载schema信息
                schema_info = None
                if self.schema_loader:
                    schema_info = self.schema_loader.load_schema()
                
                # 2. 构建提示词
                prompt = self.prompt_builder.build_sql_generation_prompt(
                    question=question,
                    db_config_id=db_config.id,
                    db_type=db_config.db_type or "mysql",
                    schema_info=schema_info,
                    context=context,
                    max_tokens=self.llm_client.max_tokens
                )
                
                # 3. 优化提示词（控制token数量）
                token_count = self.llm_client.count_tokens(prompt)
                if token_count > self.llm_client.max_tokens * 0.8:
                    prompt = self.prompt_builder.optimize_prompt(
                        prompt,
                        int(self.llm_client.max_tokens * 0.8),
                        self.llm_client.count_tokens
                    )
                
                # 4. 调用LLM生成SQL
                messages = [{"role": "user", "content": prompt}]
                response = await self.llm_client.chat_completion(
                    messages=messages,
                    temperature=self.llm_client.temperature,
                    max_tokens=self.llm_client.max_tokens
                )
                
                # 5. 提取SQL语句
                sql = self._extract_sql(response)
                
                # 6. 验证SQL安全性
                # #region agent log
                _debug_log(
                    "sql_generator.py:131",
                    "验证前SQL状态",
                    {
                        "sql_preview": sql[:300],
                        "starts_with_select": sql.upper().strip().startswith("SELECT"),
                        "starts_with_with": sql.upper().strip().startswith("WITH")
                    },
                    "C"
                )
                # #endregion
                
                self._validate_sql_safety(sql)
                
                # 7. 格式化SQL
                sql_before_format = sql
                sql = self._format_sql(sql)
                
                # #region agent log
                _debug_log(
                    "sql_generator.py:134",
                    "格式化后SQL",
                    {
                        "sql_before_length": len(sql_before_format),
                        "sql_after_length": len(sql),
                        "sql_before_preview": sql_before_format[:300],
                        "sql_after_preview": sql[:300],
                        "has_with_after": "WITH" in sql.upper(),
                        "changed": sql_before_format != sql
                    },
                    "B"
                )
                # #endregion
                
                # 8. 识别图表类型
                chart_type = self._recommend_chart_type(question, sql)
                
                # 9. 提取响应信息
                tokens_used = response.get("tokens_used", 0) if isinstance(response, dict) else 0
                model = response.get("model", self.llm_client.model_name) if isinstance(response, dict) else self.llm_client.model_name
                
                result = {
                    "sql": sql,
                    "explanation": self._generate_explanation(question, sql),
                    "chart_type": chart_type,
                    "tokens_used": tokens_used,
                    "model": model
                }
                
                # 保存到缓存（如果启用）
                if self.enable_cache and self.cache_service:
                    cache_key = self.cache_service._generate_key(
                        "sql_generation",
                        question=question,
                        db_config_id=db_config.id,
                        db_type=db_config.db_type or "mysql",
                        context_hash=hash(str(context)) if context else None
                    )
                    self.cache_service.set(cache_key, result, ttl=self.cache_ttl)
                    logger.info(f"SQL生成结果已缓存: {question[:50]}...")
                
                return result
                
            except Exception as e:
                last_error = e
                retries += 1
                logger.warning(f"SQL生成失败（尝试 {retries}/{max_retries}）: {e}")
                
                if retries >= max_retries:
                    break
        
        # 所有重试都失败，返回错误信息
        raise Exception(f"SQL生成失败（已重试{max_retries}次）: {last_error}")
    
    def _extract_sql(self, response: Dict[str, Any]) -> str:
        """
        从LLM响应中提取SQL语句
        
        Args:
            response: LLM响应
            
        Returns:
            SQL语句
        """
        # 获取响应内容
        content = ""
        if isinstance(response, dict):
            # 优先从content字段获取
            if "content" in response:
                content = response["content"]
            # 兼容OpenAI格式
            elif "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "")
            else:
                content = str(response)
        else:
            content = str(response)
        
        if not content:
            raise ValueError("LLM响应为空")
        
        # #region agent log
        _debug_log(
            "sql_generator.py:203",
            "开始提取SQL",
            {
                "content_length": len(content),
                "content_preview": content[:500],
                "has_code_block": "```" in content
            },
            "A"
        )
        # #endregion
        
        # 尝试提取SQL语句
        # 1. 查找SQL代码块
        sql_block_pattern = r"```(?:sql)?\s*\n(.*?)\n```"
        match = re.search(sql_block_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # #region agent log
            _debug_log("sql_generator.py:207", "从代码块提取", {"extracted_length": len(extracted), "extracted_preview": extracted[:300]}, "A")
            # #endregion
            return extracted
        
        # 2. 查找SELECT语句（支持WITH CTE）
        # 先尝试匹配WITH开头的CTE
        with_pattern = r"(WITH\s+\w+\s+AS\s*\([^)]+\)\s+SELECT\s+.*?)(?:;|$)"
        match = re.search(with_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # #region agent log
            _debug_log("sql_generator.py:214", "匹配WITH模式", {"extracted_length": len(extracted), "extracted_preview": extracted[:300]}, "A")
            # #endregion
            return extracted
        
        # 如果没有WITH，尝试匹配普通SELECT
        select_pattern = r"(SELECT\s+.*?)(?:;|$)"
        match = re.search(select_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # #region agent log
            _debug_log(
                "sql_generator.py:220",
                "匹配普通SELECT（可能不完整）",
                {
                    "extracted_length": len(extracted),
                    "extracted_preview": extracted[:300],
                    "has_paren_start": extracted.strip().startswith("("),
                    "select_count": extracted.upper().count("SELECT")
                },
                "A"
            )
            # #endregion
            return extracted
        
        # 3. 如果包含SQL关键字，尝试提取（支持CTE格式）
        if re.search(r"\b(SELECT|FROM|WHERE|GROUP|ORDER|LIMIT|WITH)\b", content, re.IGNORECASE):
            # 提取从WITH或SELECT开始到分号或结尾的内容
            lines = content.split("\n")
            sql_lines = []
            in_sql = False
            for line in lines:
                # 检查是否以WITH或SELECT开头（可能是CTE）
                if re.search(r"^\s*(WITH|SELECT|\()\s*SELECT\b", line, re.IGNORECASE):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    # 如果遇到分号且不在字符串中，结束提取
                    if line.strip().endswith(";") and not line.strip().endswith("';"):
                        break
            
            if sql_lines:
                sql = "\n".join(sql_lines).strip()
                # 移除末尾的分号
                sql = sql.rstrip(";")
                return sql
        
        # 4. 如果都找不到，返回原始内容（让后续验证处理）
        return content.strip()
    
    def _validate_sql_safety(self, sql: str) -> None:
        """
        验证SQL安全性
        
        检查是否包含危险的SQL操作
        
        Args:
            sql: SQL语句
            
        Raises:
            ValueError: 如果SQL不安全
        """
        sql_upper = sql.upper()
        
        # 检查是否包含危险关键字
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf"\b{keyword}\b", sql_upper):
                raise ValueError(f"SQL包含危险操作: {keyword}，只允许SELECT查询")
        
        # 检查是否以SELECT或WITH开头（支持CTE语法）
        if not re.match(r"^\s*(SELECT|WITH)", sql_upper):
            raise ValueError("SQL必须以SELECT或WITH开头，只允许查询操作")
    
    def _format_sql(self, sql: str) -> str:
        """
        格式化SQL语句，并修复缺少WITH关键字的CTE语法

        Args:
            sql: 原始SQL

        Returns:
            格式化后的SQL
        """
        # 先保留原始格式（不压缩空格），以便正确解析
        original_sql = sql
        
        # 检测并修复缺少WITH关键字的CTE语法
        sql_upper = sql.upper().strip()
        
        # 如果已经有WITH关键字，直接格式化返回
        if sql_upper.startswith('WITH'):
            sql = re.sub(r"\s+", " ", sql)
            sql = sql.strip()
            sql = sql.rstrip(";")
            return sql
        
        # 检测模式：以括号包围的SELECT开头，后面跟着另一个SELECT
        # 模式: (SELECT ... FROM ... GROUP BY ...) SELECT ... FROM 表名
        # 使用更精确的正则表达式
        cte_pattern = r'^\s*\(\s*(SELECT\s+.*?FROM\s+.*?)\s*\)\s+(SELECT\s+.*?FROM\s+(\w+).*?)(?:ORDER\s+BY|WHERE|GROUP\s+BY|LIMIT|$)'
        match = re.search(cte_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        # #region agent log
        _debug_log(
            "sql_generator.py:297",
            "CTE模式匹配尝试",
            {
                "pattern_matched": match is not None,
                "sql_starts_with_paren": sql.strip().startswith("("),
                "sql_length": len(sql),
                "sql_first_200": sql[:200]
            },
            "B"
        )
        # #endregion
        
        if match:
            # 提取CTE查询部分（括号内的SELECT）
            cte_query = match.group(1).strip()
            # 提取主查询部分
            main_query = match.group(2).strip()
            # 提取CTE名称（FROM后面的表名）
            cte_name = match.group(3).strip()
            
            # 重构SQL，添加WITH关键字
            sql = f"WITH {cte_name} AS (\n    {cte_query}\n)\n{main_query}"
            logger.info(f"检测到缺少WITH关键字的CTE，已自动修复: {cte_name}")
            
            # #region agent log
            _debug_log("sql_generator.py:310", "CTE修复成功（精确匹配）", {"cte_name": cte_name, "fixed_sql_preview": sql[:300]}, "B")
            # #endregion
        else:
            # 尝试更宽松的匹配：查找括号包围的SELECT，后面跟着SELECT
            # 手动解析括号
            if sql.strip().startswith('('):
                # #region agent log
                _debug_log("sql_generator.py:314", "开始宽松匹配（括号解析）", {"sql_starts_with_paren": True}, "E")
                # #endregion
                
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
                
                # #region agent log
                _debug_log(
                    "sql_generator.py:325",
                    "括号解析结果",
                    {
                        "cte_end": cte_end,
                        "paren_count_at_end": paren_count,
                        "sql_length": len(sql)
                    },
                    "E"
                )
                # #endregion
                
                if cte_end > 0:
                    # 检查后面是否跟着SELECT
                    remaining = sql[cte_end:].strip()
                    # #region agent log
                    _debug_log(
                        "sql_generator.py:328",
                        "检查剩余部分",
                        {
                            "remaining_preview": remaining[:200],
                            "starts_with_select": remaining.upper().startswith("SELECT")
                        },
                        "E"
                    )
                    # #endregion
                    
                    if remaining.upper().startswith('SELECT'):
                        # 提取CTE部分
                        cte_query = sql[1:cte_end-1].strip()  # 移除外层括号
                        
                        # 从主查询中提取CTE名称
                        from_match = re.search(r'FROM\s+(\w+)', remaining, re.IGNORECASE)
                        # #region agent log
                        _debug_log(
                            "sql_generator.py:334",
                            "FROM匹配结果",
                            {
                                "from_match_found": from_match is not None,
                                "cte_name": from_match.group(1) if from_match else None,
                                "remaining_preview": remaining[:200]
                            },
                            "E"
                        )
                        # #endregion
                        
                        if from_match:
                            cte_name = from_match.group(1)
                            
                            # 重构SQL
                            sql = f"WITH {cte_name} AS (\n    {cte_query}\n)\n{remaining}"
                            logger.info(f"检测到缺少WITH关键字的CTE（宽松匹配），已自动修复: {cte_name}")
                            
                            # #region agent log
                            _debug_log("sql_generator.py:339", "CTE修复成功（宽松匹配）", {"cte_name": cte_name, "fixed_sql_preview": sql[:300]}, "E")
                            # #endregion
                        else:
                            # #region agent log
                            _debug_log("sql_generator.py:340", "FROM匹配失败，无法修复", {}, "E")
                            # #endregion
                    else:
                        # #region agent log
                        _debug_log("sql_generator.py:343", "剩余部分不以SELECT开头", {"remaining_preview": remaining[:100]}, "E")
                        # #endregion
                else:
                    # #region agent log
                    _debug_log("sql_generator.py:346", "括号匹配失败", {}, "E")
                    # #endregion
            else:
                # #region agent log
                _debug_log("sql_generator.py:349", "SQL不以括号开头，跳过CTE修复", {"sql_starts_with": sql[:50]}, "B")
                # #endregion
        
        # 格式化：统一空格，但保留换行（如果已经格式化过）
        if '\n' in sql:
            # 已经格式化过，只清理多余空格
            lines = sql.split('\n')
            formatted_lines = [line.strip() for line in lines if line.strip()]
            sql = '\n'.join(formatted_lines)
        else:
            # 压缩多余空格
            sql = re.sub(r"\s+", " ", sql)
            sql = sql.strip()
        
        # 确保末尾没有分号
        sql = sql.rstrip(";")

        return sql
    
    def _recommend_chart_type(self, question: str, sql: str) -> str:
        """
        推荐图表类型
        
        Args:
            question: 用户问题
            sql: SQL语句
            
        Returns:
            推荐的图表类型：bar, line, pie, table
        """
        question_lower = question.lower()
        sql_upper = sql.upper()
        
        # 根据问题关键词判断
        if any(keyword in question_lower for keyword in ["趋势", "变化", "增长", "下降", "时间", "月份", "年份"]):
            return "line"
        
        if any(keyword in question_lower for keyword in ["占比", "比例", "百分比", "分布"]):
            return "pie"
        
        if any(keyword in question_lower for keyword in ["排名", "top", "前", "最多", "最少"]):
            return "bar"
        
        # 根据SQL特征判断
        if "GROUP BY" in sql_upper:
            # 有分组，可能是柱状图或饼图
            if "ORDER BY" in sql_upper and "DESC" in sql_upper:
                return "bar"
            return "pie"
        
        if "COUNT" in sql_upper or "SUM" in sql_upper or "AVG" in sql_upper:
            return "bar"
        
        # 默认返回表格
        return "table"
    
    def _generate_explanation(self, question: str, sql: str) -> str:
        """
        生成SQL说明
        
        Args:
            question: 用户问题
            sql: SQL语句
            
        Returns:
            SQL说明文本
        """
        return f"根据问题「{question}」生成的SQL查询语句"

