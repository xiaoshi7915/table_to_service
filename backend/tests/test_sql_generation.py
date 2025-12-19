"""
SQL生成准确性测试
测试SQL生成的准确性和质量
"""
import pytest
import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.core.llm.factory import LLMFactory
from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
from app.core.rag_langchain.rag_workflow import RAGWorkflow
from app.core.rag_langchain.schema_service import SchemaService
from app.models import DatabaseConfig, AIModelConfig
from app.core.database import get_local_db


class SQLGenerationAccuracyTest:
    """SQL生成准确性测试类"""
    
    def __init__(self, db: Session):
        """
        初始化测试
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.test_cases = self._load_test_cases()
    
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """
        加载测试用例
        
        Returns:
            测试用例列表
        """
        return [
            {
                "id": 1,
                "question": "查询所有用户的姓名和邮箱",
                "expected_keywords": ["SELECT", "name", "email", "FROM", "users"],
                "expected_tables": ["users"],
                "description": "简单查询测试"
            },
            {
                "id": 2,
                "question": "统计每个部门的员工数量",
                "expected_keywords": ["SELECT", "COUNT", "GROUP BY", "department"],
                "expected_tables": ["employees", "departments"],
                "description": "聚合查询测试"
            },
            {
                "id": 3,
                "question": "查询销售额最高的前10个产品",
                "expected_keywords": ["SELECT", "ORDER BY", "DESC", "LIMIT", "10"],
                "expected_tables": ["products", "sales"],
                "description": "排序和限制测试"
            },
            {
                "id": 4,
                "question": "查询2024年1月的订单总金额",
                "expected_keywords": ["SELECT", "SUM", "WHERE", "2024", "01"],
                "expected_tables": ["orders"],
                "description": "日期过滤和聚合测试"
            },
            {
                "id": 5,
                "question": "查询每个客户的订单数量和总金额",
                "expected_keywords": ["SELECT", "COUNT", "SUM", "GROUP BY", "JOIN"],
                "expected_tables": ["customers", "orders"],
                "description": "多表关联和聚合测试"
            }
        ]
    
    async def test_sql_generation(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig,
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试SQL生成
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            test_case: 测试用例
            
        Returns:
            测试结果
        """
        try:
            # 创建LLM客户端
            llm_client = LLMFactory.create_client(model_config)
            langchain_llm = LangChainLLMAdapter(llm_client)
            
            # 创建空的检索器（简化测试）
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
                max_retries=1  # 测试时减少重试次数
            )
            
            # 运行工作流
            result = rag_workflow.run(
                question=test_case["question"],
                db_config=db_config,
                selected_tables=test_case.get("expected_tables")
            )
            
            sql = result.get("sql", "").upper()
            
            # 检查SQL质量
            checks = {
                "has_select": "SELECT" in sql,
                "has_expected_keywords": all(
                    keyword.upper() in sql 
                    for keyword in test_case["expected_keywords"]
                ),
                "no_dangerous_operations": not any(
                    op in sql for op in ["DROP", "DELETE", "TRUNCATE", "ALTER"]
                ),
                "has_table_reference": any(
                    table.upper() in sql 
                    for table in test_case.get("expected_tables", [])
                ) if test_case.get("expected_tables") else True,
                "is_valid_format": len(sql) > 10 and sql.count("SELECT") == 1
            }
            
            accuracy_score = sum(checks.values()) / len(checks) * 100
            
            return {
                "test_case_id": test_case["id"],
                "question": test_case["question"],
                "generated_sql": result.get("sql", ""),
                "checks": checks,
                "accuracy_score": accuracy_score,
                "success": accuracy_score >= 80,  # 80%以上认为通过
                "error": result.get("error"),
                "execution_success": result.get("data") is not None
            }
            
        except Exception as e:
            logger.error(f"测试用例 {test_case['id']} 执行失败: {e}", exc_info=True)
            return {
                "test_case_id": test_case["id"],
                "question": test_case["question"],
                "generated_sql": "",
                "checks": {},
                "accuracy_score": 0,
                "success": False,
                "error": str(e),
                "execution_success": False
            }
    
    async def run_all_tests(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig
    ) -> Dict[str, Any]:
        """
        运行所有测试用例
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            
        Returns:
            测试报告
        """
        results = []
        
        for test_case in self.test_cases:
            logger.info(f"执行测试用例 {test_case['id']}: {test_case['description']}")
            result = await self.test_sql_generation(model_config, db_config, test_case)
            results.append(result)
        
        # 计算总体统计
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        avg_accuracy = sum(r["accuracy_score"] for r in results) / total_tests if total_tests > 0 else 0
        execution_success_rate = sum(1 for r in results if r.get("execution_success")) / total_tests * 100 if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
            "average_accuracy": avg_accuracy,
            "execution_success_rate": execution_success_rate,
            "results": results,
            "summary": {
                "overall_status": "PASS" if avg_accuracy >= 80 else "FAIL",
                "meets_requirement": avg_accuracy >= 80
            }
        }


# Pytest测试函数
@pytest.mark.asyncio
async def test_sql_generation_accuracy(db_session: Session):
    """SQL生成准确性测试（pytest）"""
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
    
    # 运行测试
    tester = SQLGenerationAccuracyTest(db_session)
    report = await tester.run_all_tests(model_config, db_config)
    
    # 断言
    assert report["average_accuracy"] >= 80, f"平均准确率 {report['average_accuracy']}% 低于80%"
    assert report["pass_rate"] >= 80, f"通过率 {report['pass_rate']}% 低于80%"
    
    logger.info(f"测试完成: 平均准确率 {report['average_accuracy']:.2f}%, 通过率 {report['pass_rate']:.2f}%")

