"""
初始化智能问数测试数据脚本
创建一些测试数据用于功能验证
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import User, AIModelConfig, Terminology, SQLExample, CustomPrompt, BusinessKnowledge
from app.core.password_encryption import encrypt_password
from loguru import logger


def init_test_data():
    """初始化测试数据"""
    db = LocalSessionLocal()
    
    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.error("未找到admin用户，请先创建管理员用户")
            return
        
        user_id = admin_user.id
        
        # 1. 检查是否已有AI模型配置（避免重复创建）
        existing_models = db.query(AIModelConfig).count()
        if existing_models == 0:
            logger.info("创建AI模型配置...")
            # DeepSeek配置
            deepseek_config = AIModelConfig(
                name="DeepSeek Chat",
                provider="deepseek",
                api_key=encrypt_password("sk-1da6b990e30a4fa18349e7b6e9ce9b09"),
                api_base_url="https://api.deepseek.com",
                model_name="deepseek-chat",
                max_tokens=2000,
                temperature="0.7",
                is_default=True,
                is_active=True
            )
            db.add(deepseek_config)
            logger.info("  ✓ 创建DeepSeek模型配置")
        
        # 2. 创建术语库测试数据
        existing_terminologies = db.query(Terminology).count()
        if existing_terminologies < 5:  # 如果少于5个，则添加
            logger.info("创建术语库测试数据...")
            terminologies = [
                {
                    "business_term": "销售量",
                    "db_field": "sales_amount",
                    "table_name": "sales",
                    "category": "销售类",
                    "description": "销售金额"
                },
                {
                    "business_term": "销售额",
                    "db_field": "sales_amount",
                    "table_name": "sales",
                    "category": "销售类",
                    "description": "销售金额（同义词）"
                },
                {
                    "business_term": "区域",
                    "db_field": "region",
                    "table_name": "sales",
                    "category": "地理类",
                    "description": "销售区域"
                },
                {
                    "business_term": "省份",
                    "db_field": "province",
                    "table_name": "sales",
                    "category": "地理类",
                    "description": "省份名称"
                },
                {
                    "business_term": "出货量",
                    "db_field": "shipment_quantity",
                    "table_name": "shipments",
                    "category": "物流类",
                    "description": "出货数量"
                },
                {
                    "business_term": "客户",
                    "db_field": "customer_name",
                    "table_name": "customers",
                    "category": "客户类",
                    "description": "客户名称"
                },
                {
                    "business_term": "产品",
                    "db_field": "product_name",
                    "table_name": "products",
                    "category": "产品类",
                    "description": "产品名称"
                },
                {
                    "business_term": "库存",
                    "db_field": "inventory",
                    "table_name": "products",
                    "category": "库存类",
                    "description": "库存数量"
                }
            ]
            
            created_count = 0
            for term_data in terminologies:
                # 检查是否已存在
                existing = db.query(Terminology).filter(
                    Terminology.business_term == term_data["business_term"],
                    Terminology.db_field == term_data["db_field"]
                ).first()
                
                if not existing:
                    terminology = Terminology(
                        business_term=term_data["business_term"],
                        db_field=term_data["db_field"],
                        table_name=term_data["table_name"],
                        category=term_data["category"],
                        description=term_data["description"],
                        created_by=user_id
                    )
                    db.add(terminology)
                    created_count += 1
            
            if created_count > 0:
                logger.info(f"  ✓ 创建{created_count}个术语")
            else:
                logger.info(f"  ✓ 术语库已有{existing_terminologies}个术语，跳过创建")
        
        # 3. 创建SQL示例测试数据
        existing_examples = db.query(SQLExample).count()
        if existing_examples == 0:
            logger.info("创建SQL示例测试数据...")
            sql_examples = [
                {
                    "title": "查询各区域销售量总和",
                    "question": "查询各区域的销售量总和",
                    "sql_statement": "SELECT region, SUM(sales_amount) as total_sales FROM sales GROUP BY region ORDER BY total_sales DESC",
                    "db_type": "mysql",
                    "table_name": "sales",
                    "description": "按区域统计销售总量",
                    "chart_type": "bar"
                },
                {
                    "title": "查询每月出货量",
                    "question": "查询每个月的出货量",
                    "sql_statement": "SELECT DATE_FORMAT(shipment_date, '%Y-%m') as month, SUM(shipment_quantity) as total_quantity FROM shipments GROUP BY month ORDER BY month",
                    "db_type": "mysql",
                    "table_name": "shipments",
                    "description": "按月统计出货量",
                    "chart_type": "line"
                },
                {
                    "title": "查询年度出货量排名前5的省份",
                    "question": "查询年度出货量排名前5的省份",
                    "sql_statement": "SELECT province, SUM(shipment_quantity) as total_quantity FROM shipments WHERE YEAR(shipment_date) = YEAR(CURDATE()) GROUP BY province ORDER BY total_quantity DESC LIMIT 5",
                    "db_type": "mysql",
                    "table_name": "shipments",
                    "description": "年度出货量TOP5省份",
                    "chart_type": "bar"
                },
                {
                    "title": "使用饼图展示各产品系列的年度出货占比",
                    "question": "使用饼图展示各产品系列的年度出货占比",
                    "sql_statement": "SELECT product_series, SUM(shipment_quantity) as total_quantity FROM shipments WHERE YEAR(shipment_date) = YEAR(CURDATE()) GROUP BY product_series",
                    "db_type": "mysql",
                    "table_name": "shipments",
                    "description": "产品系列年度出货占比",
                    "chart_type": "pie"
                },
                {
                    "title": "展示每个月的出货趋势",
                    "question": "展示每个月的出货趋势",
                    "sql_statement": "SELECT DATE_FORMAT(shipment_date, '%Y-%m') as month, SUM(shipment_quantity) as total_quantity FROM shipments GROUP BY month ORDER BY month",
                    "db_type": "mysql",
                    "table_name": "shipments",
                    "description": "月度出货趋势",
                    "chart_type": "line"
                },
                {
                    "title": "查询各产品的当前库存和库存状态",
                    "question": "查询各产品的当前库存和库存状态",
                    "sql_statement": "SELECT product_name, inventory, CASE WHEN inventory > 100 THEN '充足' WHEN inventory > 50 THEN '正常' ELSE '不足' END as status FROM products ORDER BY inventory DESC",
                    "db_type": "mysql",
                    "table_name": "products",
                    "description": "产品库存状态查询",
                    "chart_type": "table"
                }
            ]
            
            for example_data in sql_examples:
                sql_example = SQLExample(
                    title=example_data["title"],
                    question=example_data["question"],
                    sql_statement=example_data["sql_statement"],
                    db_type=example_data["db_type"],
                    table_name=example_data["table_name"],
                    description=example_data["description"],
                    chart_type=example_data["chart_type"],
                    created_by=user_id
                )
                db.add(sql_example)
            
            logger.info(f"  ✓ 创建{len(sql_examples)}个SQL示例")
        
        # 4. 创建自定义提示词测试数据
        existing_prompts = db.query(CustomPrompt).count()
        if existing_prompts == 0:
            logger.info("创建自定义提示词测试数据...")
            prompts = [
                {
                    "name": "SQL生成基础提示词",
                    "prompt_type": "sql_generation",
                    "content": """你是一个专业的SQL生成助手。请根据用户的问题生成准确的SQL查询语句。

要求：
1. 只生成SELECT查询语句，不要生成INSERT、UPDATE、DELETE等修改语句
2. 使用参数化查询防止SQL注入
3. 根据问题意图选择合适的聚合函数（SUM、COUNT、AVG等）
4. 合理使用GROUP BY、ORDER BY、LIMIT等子句
5. 生成的SQL要符合MySQL语法规范

用户问题：{question}
数据库表结构：{schema}
术语映射：{terminology}

请生成SQL语句：""",
                    "priority": 10,
                    "is_active": True
                },
                {
                    "name": "图表类型推荐提示词",
                    "prompt_type": "chart_recommendation",
                    "content": """根据SQL查询结果推荐合适的图表类型。

规则：
- 如果查询结果是单个数值或百分比：使用饼图
- 如果查询结果包含时间序列：使用折线图
- 如果查询结果是分类对比：使用柱状图
- 如果查询结果包含多个维度：使用表格

查询结果：{query_result}
推荐图表类型：""",
                    "priority": 5,
                    "is_active": True
                }
            ]
            
            for prompt_data in prompts:
                prompt = CustomPrompt(
                    name=prompt_data["name"],
                    prompt_type=prompt_data["prompt_type"],
                    content=prompt_data["content"],
                    priority=prompt_data["priority"],
                    is_active=prompt_data["is_active"],
                    created_by=user_id
                )
                db.add(prompt)
            
            logger.info(f"  ✓ 创建{len(prompts)}个自定义提示词")
        
        # 5. 创建业务知识库测试数据
        existing_knowledge = db.query(BusinessKnowledge).count()
        if existing_knowledge == 0:
            logger.info("创建业务知识库测试数据...")
            knowledge_items = [
                {
                    "title": "销售数据说明",
                    "content": "销售表（sales）包含以下字段：\n- sales_amount: 销售金额\n- region: 销售区域\n- sale_date: 销售日期\n- product_id: 产品ID\n\n销售金额单位为元，区域包括：华东、华南、华北、西南、西北等。",
                    "category": "数据字典",
                    "tags": "销售,数据字典,表结构"
                },
                {
                    "title": "出货量统计规则",
                    "content": "出货量统计规则：\n1. 按月份统计时，使用DATE_FORMAT函数格式化日期\n2. 年度统计时，使用YEAR函数提取年份\n3. 省份统计时，按province字段分组\n4. 产品系列统计时，按product_series字段分组",
                    "category": "业务规则",
                    "tags": "出货量,统计规则,SQL"
                },
                {
                    "title": "库存状态判断标准",
                    "content": "库存状态判断标准：\n- 库存 > 100：充足\n- 50 < 库存 <= 100：正常\n- 库存 <= 50：不足\n\n此标准适用于所有产品类型。",
                    "category": "业务规则",
                    "tags": "库存,状态,业务规则"
                }
            ]
            
            for knowledge_data in knowledge_items:
                knowledge = BusinessKnowledge(
                    title=knowledge_data["title"],
                    content=knowledge_data["content"],
                    category=knowledge_data["category"],
                    tags=knowledge_data["tags"],
                    created_by=user_id
                )
                db.add(knowledge)
            
            logger.info(f"  ✓ 创建{len(knowledge_items)}个业务知识条目")
        
        # 提交所有更改
        db.commit()
        
        logger.info("=" * 50)
        logger.info("测试数据初始化完成！")
        logger.info("=" * 50)
        
        # 打印统计信息
        print("\n数据统计：")
        print(f"  - AI模型配置: {db.query(AIModelConfig).count()} 个")
        print(f"  - 术语库: {db.query(Terminology).count()} 个")
        print(f"  - SQL示例: {db.query(SQLExample).count()} 个")
        print(f"  - 自定义提示词: {db.query(CustomPrompt).count()} 个")
        print(f"  - 业务知识库: {db.query(BusinessKnowledge).count()} 个")
        print("")
        
    except Exception as e:
        db.rollback()
        logger.error(f"初始化测试数据失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始初始化智能问数测试数据...")
    print("=" * 50)
    init_test_data()
    print("=" * 50)
    print("初始化完成！")

