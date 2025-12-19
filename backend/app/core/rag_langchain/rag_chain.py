"""
RAG链
使用LangChain实现检索增强生成
"""
from typing import Dict, Any, Optional, List
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain.base_language import BaseLanguageModel
from langchain.schema import BaseRetriever
from loguru import logger


class SQLRAGChain:
    """SQL生成RAG链"""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        retriever: BaseRetriever,
        prompt_template: Optional[str] = None,
        chain_type: str = "stuff"
    ):
        """
        初始化RAG链
        
        Args:
            llm: 大语言模型
            retriever: 检索器
            prompt_template: 提示词模板（可选）
            chain_type: 链类型（stuff/map_reduce/refine）
        """
        self.llm = llm
        self.retriever = retriever
        self.chain_type = chain_type
        
        # 默认提示词模板
        self.prompt_template = prompt_template or """
你是一个专业的SQL生成助手。请根据以下上下文信息生成SQL查询语句。

## 上下文信息
{context}

## 用户问题
{question}

## 数据库类型
{db_type}

## 要求
1. 只生成SELECT查询语句，不要生成INSERT、UPDATE、DELETE等修改语句
2. 使用参数化查询防止SQL注入（使用:param_name格式）
3. 根据问题意图选择合适的聚合函数（SUM、COUNT、AVG、MAX、MIN等）
4. 合理使用GROUP BY、ORDER BY、LIMIT等子句
5. 生成的SQL要符合{db_type}语法规范
6. 如果问题中提到了业务术语，请使用对应的数据库字段名
7. 如果上下文中有SQL示例，可以参考其写法

## 输出格式
请直接返回SQL语句，不要包含其他解释或Markdown格式。

SQL语句："""
        
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question", "db_type"]
        )
        
        # 创建RAG链
        try:
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type=chain_type,
                retriever=self.retriever,
                chain_type_kwargs={"prompt": self.prompt},
                return_source_documents=True,
                verbose=True
            )
        except Exception as e:
            logger.error(f"创建RAG链失败: {e}", exc_info=True)
            raise
    
    def generate_sql(
        self,
        question: str,
        db_type: str = "mysql"
    ) -> Dict[str, Any]:
        """
        生成SQL
        
        Args:
            question: 用户问题
            db_type: 数据库类型
            
        Returns:
            包含SQL和相关信息的字典
        """
        try:
            # 构建查询（包含db_type信息）
            query = f"{question}\n数据库类型: {db_type}"
            
            result = self.qa_chain.invoke({
                "query": query
            })
            
            # 提取SQL（可能需要从结果中提取）
            sql = result.get("result", "")
            
            # 清理SQL（移除可能的Markdown格式）
            sql = self._clean_sql(sql)
            
            return {
                "sql": sql,
                "source_documents": result.get("source_documents", []),
                "question": question
            }
        except Exception as e:
            logger.error(f"生成SQL失败: {e}", exc_info=True)
            raise
    
    def _clean_sql(self, sql: str) -> str:
        """
        清理SQL语句
        
        Args:
            sql: 原始SQL
            
        Returns:
            清理后的SQL
        """
        import re
        
        # 移除Markdown代码块
        sql = re.sub(r'```(?:sql)?\s*\n?(.*?)\n?```', r'\1', sql, flags=re.DOTALL)
        
        # 移除SQL关键字前的说明文字
        sql = re.sub(r'^.*?(?=SELECT)', '', sql, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除末尾的解释文字
        sql = re.sub(r'[;]?\s*(?:说明|解释|注意).*$', '', sql, flags=re.IGNORECASE)
        
        # 清理空白字符
        sql = ' '.join(sql.split())
        
        # 移除末尾的分号
        sql = sql.rstrip(';')
        
        return sql.strip()


