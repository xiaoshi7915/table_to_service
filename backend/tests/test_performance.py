"""
性能测试和优化
测试SQL生成的性能指标
"""
import pytest
import asyncio
import time
import statistics
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.core.llm.factory import LLMFactory
from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
from app.core.rag_langchain.rag_workflow import RAGWorkflow
from app.models import DatabaseConfig, AIModelConfig
from app.core.database import get_local_db


class PerformanceTest:
    """性能测试类"""
    
    def __init__(self, db: Session):
        """
        初始化测试
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def test_response_time(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig,
        question: str,
        iterations: int = 5
    ) -> Dict[str, Any]:
        """
        测试响应时间
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            question: 测试问题
            iterations: 迭代次数
            
        Returns:
            性能指标
        """
        response_times = []
        success_count = 0
        
        for i in range(iterations):
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
                response_times.append(elapsed_time)
                
                if result.get("error") is None:
                    success_count += 1
                    
            except Exception as e:
                elapsed_time = time.time() - start_time
                response_times.append(elapsed_time)
                logger.warning(f"第 {i+1} 次迭代失败: {e}")
        
        if not response_times:
            return {
                "question": question,
                "iterations": iterations,
                "success_rate": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "median_response_time": 0,
                "p95_response_time": 0,
                "meets_requirement": False
            }
        
        return {
            "question": question,
            "iterations": iterations,
            "success_rate": success_count / iterations * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "median_response_time": statistics.median(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0],
            "response_times": response_times,
            "meets_requirement": statistics.mean(response_times) <= 3.0  # 要求≤3秒
        }
    
    async def test_concurrent_requests(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig,
        question: str,
        concurrent_count: int = 5
    ) -> Dict[str, Any]:
        """
        测试并发请求性能
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            question: 测试问题
            concurrent_count: 并发数量
            
        Returns:
            并发性能指标
        """
        async def single_request():
            start_time = time.time()
            try:
                llm_client = LLMFactory.create_client(model_config)
                langchain_llm = LangChainLLMAdapter(llm_client)
                
                from langchain.retrievers import BaseRetriever
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
                
                rag_workflow = RAGWorkflow(
                    llm=langchain_llm,
                    terminology_retriever=EmptyRetriever(),
                    sql_example_retriever=EmptyRetriever(),
                    knowledge_retriever=EmptyRetriever(),
                    max_retries=1
                )
                
                result = rag_workflow.run(
                    question=question,
                    db_config=db_config,
                    selected_tables=None
                )
                
                elapsed_time = time.time() - start_time
                return {
                    "success": result.get("error") is None,
                    "response_time": elapsed_time,
                    "error": result.get("error")
                }
            except Exception as e:
                elapsed_time = time.time() - start_time
                return {
                    "success": False,
                    "response_time": elapsed_time,
                    "error": str(e)
                }
        
        start_time = time.time()
        tasks = [single_request() for _ in range(concurrent_count)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r["success"])
        response_times = [r["response_time"] for r in results]
        
        return {
            "concurrent_count": concurrent_count,
            "total_time": total_time,
            "throughput": concurrent_count / total_time,  # 请求/秒
            "success_rate": success_count / concurrent_count * 100,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "results": results
        }
    
    async def run_performance_tests(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig
    ) -> Dict[str, Any]:
        """
        运行完整的性能测试套件
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            
        Returns:
            性能测试报告
        """
        test_questions = [
            "查询所有用户的姓名和邮箱",
            "统计每个部门的员工数量",
            "查询销售额最高的前10个产品"
        ]
        
        response_time_results = []
        for question in test_questions:
            logger.info(f"测试响应时间: {question}")
            result = await self.test_response_time(model_config, db_config, question, iterations=5)
            response_time_results.append(result)
        
        # 并发测试
        logger.info("测试并发性能...")
        concurrent_result = await self.test_concurrent_requests(
            model_config,
            db_config,
            test_questions[0],
            concurrent_count=5
        )
        
        # 计算总体指标
        avg_response_times = [r["avg_response_time"] for r in response_time_results]
        overall_avg_time = statistics.mean(avg_response_times) if avg_response_times else 0
        
        return {
            "model_name": model_config.model_name,
            "provider": model_config.provider,
            "response_time_tests": response_time_results,
            "concurrent_test": concurrent_result,
            "overall_avg_response_time": overall_avg_time,
            "meets_requirement": overall_avg_time <= 3.0,
            "summary": {
                "avg_response_time": overall_avg_time,
                "p95_response_time": max(r["p95_response_time"] for r in response_time_results) if response_time_results else 0,
                "throughput": concurrent_result["throughput"],
                "concurrent_success_rate": concurrent_result["success_rate"]
            }
        }


# Pytest测试函数
@pytest.mark.asyncio
async def test_performance(db_session: Session):
    """性能测试（pytest）"""
    # 获取默认AI模型配置
    model_config = db_session.query(AIModelConfig).filter(
        AIModelConfig.is_default == True,
        AIModelConfig.is_active == True
    ).first()
    
    if not model_config:
        pytest.skip("未配置默认AI模型")
    
    # 获取第一个数据库配置
    db_config = db_session.query(DatabaseConfig).filter(
        DatabaseConfig.is_active == True
    ).first()
    
    if not db_config:
        pytest.skip("未配置数据库")
    
    # 运行性能测试
    tester = PerformanceTest(db_session)
    report = await tester.run_performance_tests(model_config, db_config)
    
    # 断言：平均响应时间≤3秒
    assert report["overall_avg_response_time"] <= 3.0, f"平均响应时间 {report['overall_avg_response_time']:.2f}秒 超过3秒要求"
    
    logger.info(f"性能测试完成:")
    logger.info(f"  平均响应时间: {report['overall_avg_response_time']:.2f}秒")
    logger.info(f"  P95响应时间: {report['summary']['p95_response_time']:.2f}秒")
    logger.info(f"  吞吐量: {report['summary']['throughput']:.2f} 请求/秒")
    logger.info(f"  并发成功率: {report['summary']['concurrent_success_rate']:.2f}%")

