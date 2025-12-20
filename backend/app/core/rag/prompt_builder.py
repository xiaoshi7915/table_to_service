"""
提示词构建服务
根据检索到的知识库信息构建完整的提示词
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .knowledge_retriever import KnowledgeRetriever


class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self, retriever: KnowledgeRetriever):
        """
        初始化构建器
        
        Args:
            retriever: 知识库检索器
        """
        self.retriever = retriever
    
    def build_sql_generation_prompt(
        self,
        question: str,
        db_config_id: int,
        db_type: str,
        schema_info: Optional[Dict[str, Any]] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2000
    ) -> str:
        """
        构建SQL生成提示词
        
        Args:
            question: 用户问题
            db_config_id: 数据库配置ID
            db_type: 数据库类型
            schema_info: 数据库schema信息（表结构）
            context: 对话上下文（可选）
            max_tokens: 最大token数
            
        Returns:
            完整的提示词
        """
        try:
            # 1. 检索知识库
            terminologies = self.retriever.retrieve_terminologies(question, limit=10)
            sql_examples = self.retriever.retrieve_sql_examples(question, db_type, limit=5)
            prompts = self.retriever.retrieve_prompts(question, prompt_type="sql_generation", limit=3)
            knowledge_items = self.retriever.retrieve_knowledge(question, limit=3)
            
            # 2. 构建基础提示词
            base_prompt = self._get_base_prompt(prompts)
            
            # 3. 构建术语映射部分
            terminology_section = self._build_terminology_section(terminologies)
            
            # 4. 构建SQL示例部分
            example_section = self._build_example_section(sql_examples)
            
            # 5. 构建业务知识部分
            knowledge_section = self._build_knowledge_section(knowledge_items)
            
            # 6. 构建数据库schema部分
            schema_section = self._build_schema_section(schema_info) if schema_info else ""
            
            # 7. 构建上下文部分
            context_section = self._build_context_section(context) if context else ""
            
            # 8. 组合完整提示词
            full_prompt = f"""{base_prompt}

## 术语映射
{terminology_section}

## SQL示例
{example_section}

## 业务知识
{knowledge_section}

## 数据库结构
{schema_section}

## 对话上下文
{context_section}

## 用户问题
{question}

请根据以上信息生成SQL查询语句。要求：
1. 只生成SELECT查询语句，不要生成INSERT、UPDATE、DELETE等修改语句
2. 使用参数化查询防止SQL注入
3. 根据问题意图选择合适的聚合函数（SUM、COUNT、AVG等）
4. 合理使用GROUP BY、ORDER BY、LIMIT等子句
5. 生成的SQL要符合{db_type.upper()}语法规范
6. 如果问题中提到了业务术语，请使用对应的数据库字段名
7. **重要：如果需要使用子查询或临时结果集，必须使用CTE（Common Table Expression）语法，即使用WITH关键字**
   - 格式：WITH 临时表名 AS (SELECT ...) SELECT ... FROM 临时表名
   - 示例：WITH school_stats AS (SELECT province_name, COUNT(*) AS count FROM schools_list GROUP BY province_name) SELECT * FROM school_stats WHERE count > 10
   - 如果查询需要先计算中间结果再基于该结果进行筛选或计算，必须使用WITH语句定义中间结果集
   - 不要生成只有括号包围的SELECT语句而不带WITH关键字

请直接返回SQL语句，不要包含其他解释："""
            
            return full_prompt
            
        except Exception as e:
            logger.error(f"构建SQL生成提示词失败: {e}", exc_info=True)
            # 返回简化版提示词
            return f"""请根据以下问题生成SQL查询语句（{db_type.upper()}语法）：

问题：{question}

要求：
1. 只生成SELECT查询语句
2. 使用参数化查询
3. 符合{db_type.upper()}语法规范

SQL语句："""
    
    def _get_base_prompt(self, prompts: List[Dict[str, Any]]) -> str:
        """
        获取基础提示词
        
        优先使用自定义提示词，如果没有则使用默认提示词
        
        Args:
            prompts: 检索到的提示词列表
            
        Returns:
            基础提示词内容
        """
        if prompts:
            # 使用优先级最高的提示词
            return prompts[0]["content"]
        
        # 默认提示词
        return """你是一个专业的SQL生成助手。请根据用户的问题生成准确的SQL查询语句。"""
    
    def _build_terminology_section(self, terminologies: List[Dict[str, Any]]) -> str:
        """
        构建术语映射部分
        
        Args:
            terminologies: 术语列表
            
        Returns:
            术语映射文本
        """
        if not terminologies:
            return "无相关术语映射"
        
        lines = []
        for term in terminologies:
            line = f"- {term['business_term']} -> {term['db_field']}"
            if term.get('table_name'):
                line += f" (表: {term['table_name']})"
            if term.get('description'):
                line += f" ({term['description']})"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _build_example_section(self, examples: List[Dict[str, Any]]) -> str:
        """
        构建SQL示例部分
        
        Args:
            examples: SQL示例列表
            
        Returns:
            SQL示例文本
        """
        if not examples:
            return "无相关SQL示例"
        
        sections = []
        for i, example in enumerate(examples, 1):
            section = f"""示例{i}：
问题：{example['question']}
SQL：{example['sql_statement']}"""
            if example.get('description'):
                section += f"\n说明：{example['description']}"
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def _build_knowledge_section(self, knowledge_items: List[Dict[str, Any]]) -> str:
        """
        构建业务知识部分
        
        Args:
            knowledge_items: 知识条目列表
            
        Returns:
            业务知识文本
        """
        if not knowledge_items:
            return "无相关业务知识"
        
        sections = []
        for item in knowledge_items:
            section = f"""【{item['title']}】
{item['content']}"""
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def _build_schema_section(self, schema_info: Dict[str, Any]) -> str:
        """
        构建数据库schema部分
        
        Args:
            schema_info: schema信息，格式：{
                "tables": [
                    {
                        "name": "表名",
                        "columns": [
                            {"name": "字段名", "type": "类型", "comment": "注释"}
                        ]
                    }
                ]
            }
            
        Returns:
            schema文本
        """
        if not schema_info or "tables" not in schema_info:
            return "无数据库结构信息"
        
        sections = []
        for table in schema_info["tables"]:
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            
            if not columns:
                continue
            
            section = f"表：{table_name}\n字段："
            column_lines = []
            for col in columns:
                col_line = f"  - {col.get('name', '')} ({col.get('type', '')})"
                if col.get('comment'):
                    col_line += f" - {col['comment']}"
                column_lines.append(col_line)
            
            section += "\n" + "\n".join(column_lines)
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def _build_context_section(self, context: List[Dict[str, Any]]) -> str:
        """
        构建对话上下文部分
        
        Args:
            context: 上下文列表，每个元素包含：question, sql, result
            
        Returns:
            上下文文本
        """
        if not context:
            return "无对话上下文"
        
        sections = []
        for i, ctx in enumerate(context, 1):
            section = f"""第{i}轮对话：
问题：{ctx.get('question', '')}
SQL：{ctx.get('sql', '')}"""
            if ctx.get('result_summary'):
                section += f"\n结果摘要：{ctx['result_summary']}"
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def optimize_prompt(
        self,
        prompt: str,
        max_tokens: int,
        token_counter: Any
    ) -> str:
        """
        优化提示词
        
        控制token数量，去除冗余内容
        
        Args:
            prompt: 原始提示词
            max_tokens: 最大token数
            token_counter: token计数器函数
            
        Returns:
            优化后的提示词
        """
        try:
            current_tokens = token_counter(prompt)
            
            if current_tokens <= max_tokens:
                return prompt
            
            # 如果超出限制，需要截断
            # 优先保留：基础提示词 > 术语映射 > SQL示例 > 业务知识
            logger.warning(f"提示词token数({current_tokens})超过限制({max_tokens})，需要优化")
            
            # 简单实现：截断业务知识部分
            # 实际应该更智能地选择保留哪些内容
            lines = prompt.split("\n")
            optimized_lines = []
            current_tokens = 0
            
            for line in lines:
                line_tokens = token_counter(line)
                if current_tokens + line_tokens <= max_tokens * 0.9:  # 保留10%余量
                    optimized_lines.append(line)
                    current_tokens += line_tokens
                else:
                    break
            
            optimized_prompt = "\n".join(optimized_lines)
            logger.info(f"提示词已优化：{current_tokens} tokens")
            
            return optimized_prompt
            
        except Exception as e:
            logger.error(f"优化提示词失败: {e}", exc_info=True)
            return prompt


