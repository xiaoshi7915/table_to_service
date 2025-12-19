"""
错误场景测试
测试各种错误情况下的系统行为
"""
import pytest
import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from loguru import logger

from app.core.llm.factory import LLMFactory
from app.core.rag_langchain.llm_adapter import LangChainLLMAdapter
from app.core.rag_langchain.rag_workflow import RAGWorkflow
from app.models import DatabaseConfig, AIModelConfig
from app.core.database import get_local_db


class ErrorScenarioTest:
    """错误场景测试类"""
    
    def __init__(self, db: Session):
        """
        初始化测试
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.error_scenarios = self._load_error_scenarios()
    
    def _load_error_scenarios(self) -> List[Dict[str, Any]]:
        """
        加载错误场景
        
        Returns:
            错误场景列表
        """
        return [
            {
                "id": 1,
                "name": "空问题",
                "question": "",
                "expected_behavior": "应该返回错误或提示",
                "error_type": "validation_error"
            },
            {
                "id": 2,
                "name": "不存在的表",
                "question": "查询不存在的表xxx的所有数据",
                "expected_behavior": "SQL执行失败，应该重试修正",
                "error_type": "sql_execution_error"
            },
            {
                "id": 3,
                "name": "不存在的字段",
                "question": "查询用户表中不存在的字段not_exist_field",
                "expected_behavior": "SQL执行失败，应该重试修正",
                "error_type": "sql_execution_error"
            },
            {
                "id": 4,
                "name": "SQL语法错误（由LLM生成）",
                "question": "查询所有用户，但故意使用错误的语法",
                "expected_behavior": "SQL执行失败，应该重试修正",
                "error_type": "sql_syntax_error"
            },
            {
                "id": 5,
                "name": "数据库连接失败",
                "question": "查询所有用户",
                "expected_behavior": "应该返回连接错误",
                "error_type": "connection_error",
                "simulate_connection_error": True
            },
            {
                "id": 6,
                "name": "超长问题",
                "question": "查询" + "用户" * 1000,
                "expected_behavior": "应该处理或截断",
                "error_type": "input_too_long"
            },
            {
                "id": 7,
                "name": "特殊字符注入",
                "question": "查询用户'; DROP TABLE users; --",
                "expected_behavior": "应该防止SQL注入，只生成SELECT语句",
                "error_type": "security_test"
            },
            {
                "id": 8,
                "name": "模糊问题",
                "question": "随便查点东西",
                "expected_behavior": "应该返回提示或默认查询",
                "error_type": "ambiguous_question"
            }
        ]
    
    async def test_error_scenario(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig,
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试错误场景
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            scenario: 错误场景
            
        Returns:
            测试结果
        """
        try:
            # 如果是模拟连接错误，使用无效的数据库配置
            test_db_config = db_config
            if scenario.get("simulate_connection_error"):
                # 创建一个无效的数据库配置
                from app.models import DatabaseConfig
                test_db_config = DatabaseConfig(
                    id=999999,
                    user_id=db_config.user_id,
                    name="test_invalid",
                    db_type="mysql",
                    host="invalid_host",
                    port=3306,
                    database="invalid_db",
                    username="invalid_user",
                    password="invalid_pass"
                )
            
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
                max_retries=3  # 允许重试
            )
            
            # 运行工作流
            result = rag_workflow.run(
                question=scenario["question"],
                db_config=test_db_config,
                selected_tables=None
            )
            
            # 分析结果
            has_error = result.get("error") is not None
            sql = result.get("sql", "")
            
            # 安全检查：不应该包含危险操作
            security_check = not any(
                op in sql.upper() 
                for op in ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
            ) if sql else True
            
            # 评估错误处理
            error_handled_correctly = False
            if scenario["error_type"] == "validation_error":
                error_handled_correctly = has_error or not sql  # 空问题应该返回错误或空SQL
            elif scenario["error_type"] == "sql_execution_error":
                error_handled_correctly = has_error or result.get("retry_count", 0) > 0  # 应该重试
            elif scenario["error_type"] == "security_test":
                error_handled_correctly = security_check  # 应该防止SQL注入
            elif scenario["error_type"] == "connection_error":
                error_handled_correctly = has_error  # 应该返回连接错误
            else:
                error_handled_correctly = True  # 其他情况暂不严格检查
            
            return {
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "question": scenario["question"],
                "error_type": scenario["error_type"],
                "has_error": has_error,
                "error_message": result.get("error", ""),
                "generated_sql": sql,
                "security_check_passed": security_check,
                "error_handled_correctly": error_handled_correctly,
                "retry_count": result.get("retry_count", 0),
                "success": error_handled_correctly and security_check
            }
            
        except Exception as e:
            logger.error(f"错误场景 {scenario['id']} 测试异常: {e}", exc_info=True)
            return {
                "scenario_id": scenario["id"],
                "scenario_name": scenario["name"],
                "question": scenario["question"],
                "error_type": scenario["error_type"],
                "has_error": True,
                "error_message": str(e),
                "generated_sql": "",
                "security_check_passed": True,
                "error_handled_correctly": False,
                "retry_count": 0,
                "success": False
            }
    
    async def run_all_error_tests(
        self,
        model_config: AIModelConfig,
        db_config: DatabaseConfig
    ) -> Dict[str, Any]:
        """
        运行所有错误场景测试
        
        Args:
            model_config: AI模型配置
            db_config: 数据库配置
            
        Returns:
            测试报告
        """
        results = []
        
        for scenario in self.error_scenarios:
            logger.info(f"测试错误场景 {scenario['id']}: {scenario['name']}")
            result = await self.test_error_scenario(model_config, db_config, scenario)
            results.append(result)
        
        # 计算统计
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        security_passed = sum(1 for r in results if r["security_check_passed"])
        
        return {
            "total_scenarios": total_tests,
            "passed_scenarios": passed_tests,
            "failed_scenarios": total_tests - passed_tests,
            "pass_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
            "security_pass_rate": security_passed / total_tests * 100 if total_tests > 0 else 0,
            "results": results,
            "summary": {
                "overall_status": "PASS" if passed_tests >= total_tests * 0.8 else "FAIL",
                "security_status": "PASS" if security_passed == total_tests else "FAIL",
                "meets_requirement": passed_tests >= total_tests * 0.8 and security_passed == total_tests
            }
        }


# Pytest测试函数
@pytest.mark.asyncio
async def test_error_scenarios(db_session: Session):
    """错误场景测试（pytest）"""
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
    
    # 运行错误场景测试
    tester = ErrorScenarioTest(db_session)
    report = await tester.run_all_error_tests(model_config, db_config)
    
    # 断言
    assert report["pass_rate"] >= 80, f"错误场景通过率 {report['pass_rate']}% 低于80%"
    assert report["security_pass_rate"] == 100, f"安全检查通过率 {report['security_pass_rate']}% 未达到100%"
    
    logger.info(f"错误场景测试完成:")
    logger.info(f"  通过率: {report['pass_rate']:.2f}%")
    logger.info(f"  安全检查通过率: {report['security_pass_rate']:.2f}%")

