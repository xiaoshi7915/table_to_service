"""
SQL生成服务
调用LLM生成SQL，并进行验证和优化
支持缓存机制以提升性能
"""
import re
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.llm.base import BaseLLMClient
from app.core.rag.prompt_builder import PromptBuilder
from app.core.rag.schema_loader import SchemaLoader
from app.core.cache import get_cache_service
from app.models import DatabaseConfig


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
                self._validate_sql_safety(sql)
                
                # 7. 格式化SQL
                sql = self._format_sql(sql)
                
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
        
        # 尝试提取SQL语句
        # 1. 查找SQL代码块
        sql_block_pattern = r"```(?:sql)?\s*\n(.*?)\n```"
        match = re.search(sql_block_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 2. 查找SELECT语句
        select_pattern = r"(SELECT\s+.*?)(?:;|$)"
        match = re.search(select_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 3. 如果包含SQL关键字，尝试提取
        if re.search(r"\b(SELECT|FROM|WHERE|GROUP|ORDER|LIMIT)\b", content, re.IGNORECASE):
            # 提取从SELECT开始到分号或结尾的内容
            lines = content.split("\n")
            sql_lines = []
            in_sql = False
            for line in lines:
                if re.search(r"\bSELECT\b", line, re.IGNORECASE):
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if line.strip().endswith(";"):
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
        
        # 检查是否以SELECT开头
        if not re.match(r"^\s*SELECT", sql_upper):
            raise ValueError("SQL必须以SELECT开头，只允许查询操作")
    
    def _format_sql(self, sql: str) -> str:
        """
        格式化SQL语句
        
        Args:
            sql: 原始SQL
            
        Returns:
            格式化后的SQL
        """
        # 移除多余的空格和换行
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

