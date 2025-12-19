"""
不同模型对比测试
对比不同AI模型的SQL生成效果
"""
import pytest
import asyncio
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.core.llm.factory import LLMFactory
from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
from app.core.rag_langchain.rag_workflow import RAGWorkflow
from app.models import DatabaseConfig, AIModelConfig
from app.core.database import get_local_db


class ModelComparisonTest:
    """模型对比测试类"""
    
    def __init__(self, db: Session):
        """
        初始化测试
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.test_questions = [
            "查询所有用户的姓名和邮箱",
            "统计每个部门的员工数量",
            "查询销售额最高的前10个产品",
            "查询2024年1月的订单总金额",
            "查询每个客户的订单数量和总金额"
        ]
    
    async def test_model(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig,
        question: str
    ) -> Dict[str, Any]:
        """
        测试单个模型
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            question: 测试问题
            
        Returns:
            测试结果
        """
        start_time = time.time()
        
        try:
            # 创建LLM客户端
            llm_client = LLMFactory.create_client(model_config)
            langchain_llm = LangChainLLMAdapter(llm_client)
            
            # 创建空的检索器
            try:
                from langchain_core.retrievers import BaseRetriever
            except ImportError:
                try:
                    from langchain.retrievers import BaseRetriever
                except ImportError:
                    from langchain.schema import BaseRetriever
            
            class EmptyRetriever(BaseRetriever):
                def _get_relevant_documents(self, query: str):
                    return []
                async def _aget_relevant_documents(self, query: str):
                    return []
                
                # LangChain 1.x兼容方法
                def get_relevant_documents(self, query: str):
                    return []
                async def aget_relevant_documents(self, query: str):
                    return []
            
            # 创建RAG工作流
            rag_workflow = RAGWorkflow(
                llm=langchain_llm,
                terminology_retriever=EmptyRetriever(),
                sql_example_retriever=EmptyRetriever(),
                knowledge_retriever=EmptyRetriever(),
                max_retries=1
            )
            
            # 运行工作流
            result = rag_workflow.run(
                question=question,
                db_config=db_config,
                selected_tables=None
            )
            
            elapsed_time = time.time() - start_time
            
            sql = result.get("sql", "")
            
            # 评估SQL质量
            quality_score = self._evaluate_sql_quality(sql, question)
            
            return {
                "model_name": model_config.model_name,
                "provider": model_config.provider,
                "question": question,
                "sql": sql,
                "quality_score": quality_score,
                "response_time": elapsed_time,
                "success": result.get("error") is None,
                "has_data": result.get("data") is not None,
                "data_count": len(result.get("data", [])),
                "error": result.get("error")
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"模型 {model_config.model_name} 测试失败: {e}", exc_info=True)
            return {
                "model_name": model_config.model_name,
                "provider": model_config.provider,
                "question": question,
                "sql": "",
                "quality_score": 0,
                "response_time": elapsed_time,
                "success": False,
                "has_data": False,
                "data_count": 0,
                "error": str(e)
            }
    
    def _evaluate_sql_quality(self, sql: str, question: str) -> float:
        """
        评估SQL质量
        
        Args:
            sql: 生成的SQL
            question: 原始问题
            
        Returns:
            质量分数 (0-100)
        """
        if not sql:
            return 0
        
        sql_upper = sql.upper()
        score = 0
        
        # 基本结构检查 (30分)
        if "SELECT" in sql_upper:
            score += 10
        if "FROM" in sql_upper:
            score += 10
        if sql.count("SELECT") == 1:  # 只有一个SELECT
            score += 10
        
        # 安全性检查 (20分)
        dangerous_ops = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
        if not any(op in sql_upper for op in dangerous_ops):
            score += 20
        
        # 语法完整性 (30分)
        if "SELECT" in sql_upper and "FROM" in sql_upper:
            score += 15
        if sql.count("(") == sql.count(")"):  # 括号匹配
            score += 10
        if len(sql.strip()) > 20:  # 长度合理
            score += 5
        
        # 问题相关性 (20分)
        question_lower = question.lower()
        if "统计" in question or "数量" in question:
            if "COUNT" in sql_upper:
                score += 10
        if "总和" in question or "总金额" in question or "总计" in question:
            if "SUM" in sql_upper:
                score += 10
        if "最高" in question or "最大" in question or "前" in question:
            if "ORDER BY" in sql_upper or "LIMIT" in sql_upper or "MAX" in sql_upper:
                score += 10
        if "平均" in question:
            if "AVG" in sql_upper:
                score += 10
        
        return min(score, 100)
    
    async def compare_models(
        self,
        model_configs: List[AIModelConfig],
        db_config: DatabaseConfig
    ) -> Dict[str, Any]:
        """
        对比多个模型
        
        Args:
            model_configs: 模型配置列表
            db_config: 数据库配置
            
        Returns:
            对比报告
        """
        comparison_results = []
        
        for model_config in model_configs:
            logger.info(f"测试模型: {model_config.provider} - {model_config.model_name}")
            
            model_results = []
            total_time = 0
            success_count = 0
            
            for question in self.test_questions:
                result = await self.test_model(model_config, db_config, question)
                model_results.append(result)
                total_time += result["response_time"]
                if result["success"]:
                    success_count += 1
            
            avg_quality = sum(r["quality_score"] for r in model_results) / len(model_results) if model_results else 0
            avg_time = total_time / len(self.test_questions) if self.test_questions else 0
            
            comparison_results.append({
                "model_name": model_config.model_name,
                "provider": model_config.provider,
                "average_quality_score": avg_quality,
                "average_response_time": avg_time,
                "success_rate": success_count / len(self.test_questions) * 100 if self.test_questions else 0,
                "results": model_results
            })
        
        # 排序（按质量分数）
        comparison_results.sort(key=lambda x: x["average_quality_score"], reverse=True)
        
        return {
            "test_questions": self.test_questions,
            "models_tested": len(model_configs),
            "comparison_results": comparison_results,
            "best_model": comparison_results[0] if comparison_results else None,
            "fastest_model": min(comparison_results, key=lambda x: x["average_response_time"]) if comparison_results else None
        }


# Pytest测试函数
@pytest.mark.asyncio
async def test_model_comparison(db_session: Session):
    """模型对比测试（pytest）"""
    # 获取所有激活的AI模型配置
    model_configs = db_session.query(AIModelConfig).filter(
        AIModelConfig.is_active == True
    ).all()
    
    if len(model_configs) < 2:
        pytest.skip("至少需要2个激活的AI模型进行对比")
    
    # 获取第一个数据库配置
    db_config = db_session.query(DatabaseConfig).filter(
        DatabaseConfig.is_active == True
    ).first()
    
    if not db_config:
        pytest.skip("未配置数据库")
    
    # 运行对比测试
    tester = ModelComparisonTest(db_session)
    report = await tester.compare_models(model_configs, db_config)
    
    # 输出结果
    logger.info(f"模型对比测试完成，测试了 {report['models_tested']} 个模型")
    logger.info(f"最佳模型: {report['best_model']['model_name']} (质量分数: {report['best_model']['average_quality_score']:.2f})")
    logger.info(f"最快模型: {report['fastest_model']['model_name']} (平均响应时间: {report['fastest_model']['average_response_time']:.2f}秒)")
    
    # 断言：至少有一个模型质量分数>=80
    assert report['best_model']['average_quality_score'] >= 80, "没有模型达到80%的质量要求"

