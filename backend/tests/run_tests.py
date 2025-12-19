"""
运行所有测试的脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import get_local_db
from app.models import AIModelConfig, DatabaseConfig
from tests.test_sql_generation import SQLGenerationAccuracyTest
from tests.test_model_comparison import ModelComparisonTest
from tests.test_performance import PerformanceTest
from tests.test_error_scenarios import ErrorScenarioTest
from loguru import logger


async def main():
    """运行所有测试"""
    # 获取数据库会话
    db = next(get_local_db())
    
    try:
        # 获取默认AI模型配置
        model_config = db.query(AIModelConfig).filter(
            AIModelConfig.is_default == True,
            AIModelConfig.is_active == True
        ).first()
        
        if not model_config:
            logger.error("未配置默认AI模型，请先配置AI模型")
            return
        
        # 获取第一个数据库配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.is_active == True
        ).first()
        
        if not db_config:
            logger.error("未配置数据库，请先配置数据库")
            return
        
        logger.info("=" * 60)
        logger.info("开始运行测试套件")
        logger.info("=" * 60)
        
        # 1. SQL生成准确性测试
        logger.info("\n[1/4] SQL生成准确性测试")
        logger.info("-" * 60)
        accuracy_tester = SQLGenerationAccuracyTest(db)
        accuracy_report = await accuracy_tester.run_all_tests(model_config, db_config)
        logger.info(f"平均准确率: {accuracy_report['average_accuracy']:.2f}%")
        logger.info(f"通过率: {accuracy_report['pass_rate']:.2f}%")
        logger.info(f"状态: {'✅ 通过' if accuracy_report['summary']['meets_requirement'] else '❌ 未通过'}")
        
        # 2. 模型对比测试
        logger.info("\n[2/4] 模型对比测试")
        logger.info("-" * 60)
        model_configs = db.query(AIModelConfig).filter(
            AIModelConfig.is_active == True
        ).all()
        
        if len(model_configs) >= 2:
            comparison_tester = ModelComparisonTest(db)
            comparison_report = await comparison_tester.compare_models(model_configs, db_config)
            logger.info(f"测试了 {comparison_report['models_tested']} 个模型")
            if comparison_report['best_model']:
                logger.info(f"最佳模型: {comparison_report['best_model']['model_name']} "
                          f"(质量分数: {comparison_report['best_model']['average_quality_score']:.2f})")
        else:
            logger.warning("至少需要2个激活的AI模型进行对比，跳过此测试")
        
        # 3. 性能测试
        logger.info("\n[3/4] 性能测试")
        logger.info("-" * 60)
        performance_tester = PerformanceTest(db)
        performance_report = await performance_tester.run_performance_tests(model_config, db_config)
        logger.info(f"平均响应时间: {performance_report['overall_avg_response_time']:.2f}秒")
        logger.info(f"P95响应时间: {performance_report['summary']['p95_response_time']:.2f}秒")
        logger.info(f"吞吐量: {performance_report['summary']['throughput']:.2f} 请求/秒")
        logger.info(f"状态: {'✅ 通过' if performance_report['meets_requirement'] else '❌ 未通过'}")
        
        # 4. 错误场景测试
        logger.info("\n[4/4] 错误场景测试")
        logger.info("-" * 60)
        error_tester = ErrorScenarioTest(db)
        error_report = await error_tester.run_all_error_tests(model_config, db_config)
        logger.info(f"通过率: {error_report['pass_rate']:.2f}%")
        logger.info(f"安全检查通过率: {error_report['security_pass_rate']:.2f}%")
        logger.info(f"状态: {'✅ 通过' if error_report['summary']['meets_requirement'] else '❌ 未通过'}")
        
        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("测试总结")
        logger.info("=" * 60)
        logger.info(f"SQL生成准确性: {'✅' if accuracy_report['summary']['meets_requirement'] else '❌'}")
        logger.info(f"性能要求: {'✅' if performance_report['meets_requirement'] else '❌'}")
        logger.info(f"错误处理: {'✅' if error_report['summary']['meets_requirement'] else '❌'}")
        
        overall_pass = (
            accuracy_report['summary']['meets_requirement'] and
            performance_report['meets_requirement'] and
            error_report['summary']['meets_requirement']
        )
        
        logger.info(f"\n总体状态: {'✅ 所有测试通过' if overall_pass else '❌ 部分测试未通过'}")
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

