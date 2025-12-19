"""
全面测试所有数据库类型的连接和功能
用于验证多数据源支持的完整性
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import DatabaseConfig
from app.core.db_factory import DatabaseConnectionFactory
from app.core.sql_dialect import SQLDialectFactory
from sqlalchemy import text, inspect
from loguru import logger

def test_database_connection(config: DatabaseConfig):
    """测试单个数据库配置的完整流程"""
    db_type = config.db_type or "mysql"
    
    print("\n" + "=" * 70)
    print(f"测试数据库配置: {config.name} (ID: {config.id})")
    print(f"数据库类型: {db_type.upper()}")
    print(f"主机: {config.host}:{config.port}" if db_type != "sqlite" else f"文件路径: {config.database}")
    if db_type != "sqlite":
        print(f"数据库: {config.database}")
        print(f"用户名: {config.username}")
    print("=" * 70)
    
    results = {
        "connection": False,
        "test_sql": False,
        "table_list": False,
        "table_count": 0,
        "errors": []
    }
    
    try:
        # 1. 测试创建引擎
        print("\n[1/4] 创建数据库引擎...")
        try:
            engine = DatabaseConnectionFactory.create_engine(config)
            print("  ✓ 引擎创建成功")
            results["connection"] = True
        except Exception as e:
            error_msg = f"引擎创建失败: {e}"
            print(f"  ✗ {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # 2. 测试连接
        print("\n[2/4] 测试数据库连接...")
        try:
            test_sql = DatabaseConnectionFactory.get_test_sql(db_type)
            with engine.connect() as conn:
                conn.execute(text(test_sql))
            print(f"  ✓ 连接测试成功 (SQL: {test_sql})")
            results["test_sql"] = True
        except Exception as e:
            error_msg = f"连接测试失败: {e}"
            print(f"  ✗ {error_msg}")
            results["errors"].append(error_msg)
            engine.dispose()
            return results
        
        # 3. 获取表列表
        print("\n[3/4] 获取表列表...")
        adapter = SQLDialectFactory.get_adapter(db_type)
        table_names = []
        
        try:
            with engine.connect() as conn:
                if db_type == "sqlite":
                    # SQLite特殊处理
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                    table_names = [row[0] for row in result]
                elif db_type == "postgresql":
                    # PostgreSQL需要指定schema
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names(schema='public')
                    if not table_names:
                        # 回退到SQL查询
                        query = adapter.get_table_names_query(schema='public')
                        result = conn.execute(text(query))
                        table_names = [row[0] if isinstance(row, (tuple, list)) else str(row) for row in result]
                elif db_type == "sqlserver":
                    # SQL Server
                    try:
                        inspector = inspect(engine)
                        table_names = inspector.get_table_names()
                    except:
                        query = adapter.get_table_names_query()
                        result = conn.execute(text(query))
                        table_names = [row[0] for row in result]
                elif db_type == "oracle":
                    # Oracle
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
                else:
                    # MySQL和其他
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
            
            # 确保是列表
            if not isinstance(table_names, list):
                table_names = list(table_names) if table_names else []
            
            results["table_count"] = len(table_names)
            if table_names:
                print(f"  ✓ 获取到 {len(table_names)} 个表")
                print(f"    表名: {', '.join(table_names[:5])}{'...' if len(table_names) > 5 else ''}")
                results["table_list"] = True
            else:
                print(f"  ⚠ 表列表为空（可能是数据库中没有表）")
                results["table_list"] = True  # 空列表也算成功
            
        except Exception as e:
            error_msg = f"获取表列表失败: {e}"
            print(f"  ✗ {error_msg}")
            results["errors"].append(error_msg)
        
        # 4. 测试获取表信息（如果有表）
        if table_names:
            print("\n[4/4] 测试获取表信息...")
            test_table = table_names[0]
            try:
                with engine.connect() as conn:
                    inspector = inspect(engine)
                    columns = inspector.get_columns(test_table)
                    pk_constraint = inspector.get_pk_constraint(test_table)
                    primary_keys = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                    
                    print(f"  ✓ 成功获取表 '{test_table}' 的信息")
                    print(f"    字段数: {len(columns)}")
                    print(f"    主键: {', '.join(primary_keys) if primary_keys else '无'}")
            except Exception as e:
                error_msg = f"获取表信息失败: {e}"
                print(f"  ✗ {error_msg}")
                results["errors"].append(error_msg)
        else:
            print("\n[4/4] 跳过表信息测试（没有表）")
        
        engine.dispose()
        
    except Exception as e:
        error_msg = f"测试过程出错: {e}"
        print(f"  ✗ {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "-" * 70)
    print("测试结果:")
    print(f"  连接: {'✓' if results['connection'] else '✗'}")
    print(f"  测试SQL: {'✓' if results['test_sql'] else '✗'}")
    print(f"  表列表: {'✓' if results['table_list'] else '✗'} ({results['table_count']} 个表)")
    if results["errors"]:
        print(f"  错误: {len(results['errors'])} 个")
        for err in results["errors"]:
            print(f"    - {err}")
    print("-" * 70)
    
    return results


def test_all_databases():
    """测试所有数据库配置"""
    db = LocalSessionLocal()
    try:
        # 获取所有数据库配置
        configs = db.query(DatabaseConfig).filter(DatabaseConfig.is_active == True).all()
        
        if not configs:
            print("未找到任何激活的数据库配置")
            return
        
        print("=" * 70)
        print(f"找到 {len(configs)} 个激活的数据库配置")
        print("=" * 70)
        
        # 按数据库类型分组
        by_type = {}
        for config in configs:
            db_type = config.db_type or "mysql"
            if db_type not in by_type:
                by_type[db_type] = []
            by_type[db_type].append(config)
        
        # 显示统计
        print("\n数据库类型分布:")
        for db_type, configs_list in by_type.items():
            print(f"  {db_type.upper()}: {len(configs_list)} 个配置")
        
        # 测试每个配置
        all_results = {}
        for config in configs:
            results = test_database_connection(config)
            all_results[config.id] = {
                "name": config.name,
                "type": config.db_type or "mysql",
                "results": results
            }
        
        # 总体统计
        print("\n" + "=" * 70)
        print("总体测试结果")
        print("=" * 70)
        
        success_count = 0
        fail_count = 0
        
        for config_id, info in all_results.items():
            results = info["results"]
            if results["connection"] and results["test_sql"]:
                success_count += 1
                status = "✓"
            else:
                fail_count += 1
                status = "✗"
            
            print(f"{status} {info['name']} ({info['type']}) - "
                  f"连接:{'✓' if results['connection'] else '✗'} "
                  f"测试:{'✓' if results['test_sql'] else '✗'} "
                  f"表列表:{'✓' if results['table_list'] else '✗'} "
                  f"({results['table_count']} 个表)")
        
        print("\n" + "-" * 70)
        print(f"总计: {len(all_results)} 个配置")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")
        print("-" * 70)
        
    except Exception as e:
        print(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_specific_database_type(db_type: str):
    """测试特定数据库类型的所有配置"""
    db = LocalSessionLocal()
    try:
        configs = db.query(DatabaseConfig).filter(
            DatabaseConfig.db_type == db_type,
            DatabaseConfig.is_active == True
        ).all()
        
        if not configs:
            print(f"未找到 {db_type.upper()} 类型的数据库配置")
            return
        
        print(f"找到 {len(configs)} 个 {db_type.upper()} 数据库配置")
        
        for config in configs:
            test_database_connection(config)
        
    except Exception as e:
        print(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 测试特定数据库类型
        db_type = sys.argv[1].lower()
        test_specific_database_type(db_type)
    else:
        # 测试所有数据库
        test_all_databases()

