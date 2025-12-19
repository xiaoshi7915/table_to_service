"""
图表生成准确性测试
"""
import pytest
from typing import Dict, Any, List
from app.core.rag_langchain.chart_service import ChartService


class ChartGenerationAccuracyTest:
    """图表生成准确性测试类"""
    
    def __init__(self):
        self.chart_service = ChartService()
        self.test_cases = self._load_test_cases()
    
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """加载测试用例"""
        return [
            {
                "id": 1,
                "question": "查询每个部门的员工数量",
                "data": [
                    {"部门": "技术部", "数量": 10},
                    {"部门": "销售部", "数量": 8},
                    {"部门": "市场部", "数量": 5}
                ],
                "expected_type": "bar",
                "description": "柱状图测试 - 分组统计"
            },
            {
                "id": 2,
                "question": "查看销售额的趋势变化",
                "data": [
                    {"月份": "1月", "销售额": 10000},
                    {"月份": "2月", "销售额": 12000},
                    {"月份": "3月", "销售额": 15000}
                ],
                "expected_type": "line",
                "description": "折线图测试 - 趋势分析"
            },
            {
                "id": 3,
                "question": "各部门员工占比",
                "data": [
                    {"部门": "技术部", "数量": 10},
                    {"部门": "销售部", "数量": 8},
                    {"部门": "市场部", "数量": 5}
                ],
                "expected_type": "pie",
                "description": "饼图测试 - 占比分析"
            },
            {
                "id": 4,
                "question": "查询所有用户信息",
                "data": [
                    {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
                    {"id": 2, "name": "李四", "email": "lisi@example.com"}
                ],
                "expected_type": "table",
                "description": "表格测试 - 明细数据"
            },
            {
                "id": 5,
                "question": "分析价格和销量的关系",
                "data": [
                    {"价格": 100, "销量": 50},
                    {"价格": 200, "销量": 30},
                    {"价格": 300, "销量": 20}
                ],
                "expected_type": "scatter",
                "description": "散点图测试 - 关系分析"
            }
        ]
    
    def test_chart_generation(
        self,
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试图表生成
        
        Args:
            test_case: 测试用例
            
        Returns:
            测试结果
        """
        try:
            # 生成图表配置
            chart_config = self.chart_service.generate_chart_config(
                question=test_case["question"],
                data=test_case["data"]
            )
            
            # 检查图表类型
            chart_type = chart_config.get("type")
            type_match = chart_type == test_case["expected_type"]
            
            # 检查配置完整性
            has_title = "title" in chart_config or chart_type == "table"
            has_data = True
            
            if chart_type == "bar":
                has_data = "xAxis" in chart_config and "series" in chart_config
            elif chart_type == "line":
                has_data = "xAxis" in chart_config and "series" in chart_config
            elif chart_type == "pie":
                has_data = "series" in chart_config
            elif chart_type == "scatter":
                has_data = "xAxis" in chart_config and "series" in chart_config
            elif chart_type == "table":
                has_data = "columns" in chart_config and "data" in chart_config
            
            accuracy_score = sum([
                type_match,
                has_title,
                has_data
            ]) / 3 * 100
            
            return {
                "test_case_id": test_case["id"],
                "question": test_case["question"],
                "expected_type": test_case["expected_type"],
                "actual_type": chart_type,
                "type_match": type_match,
                "has_title": has_title,
                "has_data": has_data,
                "accuracy_score": accuracy_score,
                "success": accuracy_score >= 80,
                "chart_config": chart_config
            }
            
        except Exception as e:
            return {
                "test_case_id": test_case["id"],
                "question": test_case["question"],
                "expected_type": test_case["expected_type"],
                "actual_type": None,
                "type_match": False,
                "has_title": False,
                "has_data": False,
                "accuracy_score": 0,
                "success": False,
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        results = []
        
        for test_case in self.test_cases:
            result = self.test_chart_generation(test_case)
            results.append(result)
        
        # 计算统计
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        avg_accuracy = sum(r["accuracy_score"] for r in results) / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
            "average_accuracy": avg_accuracy,
            "results": results,
            "summary": {
                "overall_status": "PASS" if avg_accuracy >= 80 else "FAIL",
                "meets_requirement": avg_accuracy >= 80
            }
        }


# Pytest测试函数
def test_chart_generation_accuracy():
    """图表生成准确性测试（pytest）"""
    tester = ChartGenerationAccuracyTest()
    report = tester.run_all_tests()
    
    # 断言
    assert report["average_accuracy"] >= 80, f"平均准确率 {report['average_accuracy']}% 低于80%"
    assert report["pass_rate"] >= 80, f"通过率 {report['pass_rate']}% 低于80%"

