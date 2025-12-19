"""
大数据量性能测试
"""
import pytest
import time
from typing import Dict, Any, List
from app.core.rag_langchain.chart_service import ChartService
from app.core.rag_langchain.sql_executor import SQLExecutor
from app.models import DatabaseConfig, AIModelConfig
from sqlalchemy.orm import Session


class LargeDataPerformanceTest:
    """大数据量性能测试类"""
    
    def __init__(self):
        self.chart_service = ChartService()
    
    def test_chart_generation_performance(
        self,
        data_sizes: List[int] = [100, 500, 1000, 5000]
    ) -> Dict[str, Any]:
        """
        测试图表生成性能
        
        Args:
            data_sizes: 数据量列表
            
        Returns:
            性能测试结果
        """
        results = []
        
        for size in data_sizes:
            # 生成测试数据
            test_data = [
                {"列1": f"值{i}", "列2": i * 10, "列3": i * 5}
                for i in range(size)
            ]
            
            # 测试图表生成时间
            start_time = time.time()
            chart_config = self.chart_service.generate_chart_config(
                question="测试大数据量图表生成",
                data=test_data
            )
            elapsed_time = time.time() - start_time
            
            results.append({
                "data_size": size,
                "elapsed_time": elapsed_time,
                "success": chart_config is not None,
                "chart_type": chart_config.get("type") if chart_config else None
            })
        
        return {
            "results": results,
            "average_time": sum(r["elapsed_time"] for r in results) / len(results) if results else 0,
            "max_time": max(r["elapsed_time"] for r in results) if results else 0,
            "min_time": min(r["elapsed_time"] for r in results) if results else 0
        }
    
    def test_sql_execution_performance(
        self,
        db_config: DatabaseConfig,
        sql: str,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """
        测试SQL执行性能
        
        Args:
            db_config: 数据库配置
            sql: SQL语句
            iterations: 迭代次数
            
        Returns:
            性能测试结果
        """
        executor = SQLExecutor(db_config, timeout=30, max_rows=10000)
        
        execution_times = []
        success_count = 0
        
        for i in range(iterations):
            start_time = time.time()
            result = executor.execute(sql)
            elapsed_time = time.time() - start_time
            
            execution_times.append(elapsed_time)
            if result.get("success"):
                success_count += 1
        
        return {
            "iterations": iterations,
            "success_count": success_count,
            "success_rate": success_count / iterations * 100,
            "average_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "max_time": max(execution_times) if execution_times else 0,
            "min_time": min(execution_times) if execution_times else 0,
            "p95_time": sorted(execution_times)[int(len(execution_times) * 0.95)] if execution_times else 0
        }


# Pytest测试函数
def test_chart_generation_performance():
    """图表生成性能测试（pytest）"""
    tester = LargeDataPerformanceTest()
    report = tester.test_chart_generation_performance([100, 500, 1000, 5000])
    
    # 断言：平均时间应该小于1秒
    assert report["average_time"] < 1.0, f"平均生成时间 {report['average_time']:.2f}秒 超过1秒"
    assert report["max_time"] < 2.0, f"最大生成时间 {report['max_time']:.2f}秒 超过2秒"


@pytest.mark.asyncio
async def test_sql_execution_performance(db_session: Session):
    """SQL执行性能测试（pytest）"""
    # 获取数据库配置
    from app.models import DatabaseConfig
    db_config = db_session.query(DatabaseConfig).filter(
        DatabaseConfig.is_active == True
    ).first()
    
    if not db_config:
        pytest.skip("未配置数据库")
    
    tester = LargeDataPerformanceTest()
    
    # 测试简单查询
    simple_sql = "SELECT * FROM users LIMIT 1000"
    report = tester.test_sql_execution_performance(db_config, simple_sql, iterations=5)
    
    # 断言：平均时间应该小于3秒
    assert report["average_time"] < 3.0, f"平均执行时间 {report['average_time']:.2f}秒 超过3秒"
    assert report["success_rate"] >= 80, f"成功率 {report['success_rate']}% 低于80%"

