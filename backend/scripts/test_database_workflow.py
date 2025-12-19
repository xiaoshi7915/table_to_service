"""
测试数据库完整工作流程
模拟用户操作流程：创建配置 -> 测试连接 -> 获取表列表 -> 获取表信息 -> 创建接口 -> 执行接口
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import DatabaseConfig, InterfaceConfig
from app.core.db_factory import DatabaseConnectionFactory
from app.core.sql_dialect import SQLDialectFactory
from app.core.password_encryption import encrypt_password
from sqlalchemy import text, inspect
from loguru import logger

def test_complete_workflow(config_id: int):
    """测试完整的数据库工作流程"""
    db = LocalSessionLocal()
    try:
        config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config_id).first()
        
        if not config:
            print(f"配置ID {config_id} 不存在")
            return
        
        db_type = config.db_type or "mysql"
        print("=" * 70)
        print(f"测试完整工作流程: {config.name} ({db_type.upper()})")
        print("=" * 70)
        
        # 步骤1: 测试连接
        print("\n[步骤1] 测试数据库连接...")
        try:
            engine = DatabaseConnectionFactory.create_engine(config)
            test_sql = DatabaseConnectionFactory.get_test_sql(db_type)
            with engine.connect() as conn:
                conn.execute(text(test_sql))
            print("  ✓ 连接成功")
        except Exception as e:
            print(f"  ✗ 连接失败: {e}")
            return
        
        # 步骤2: 获取表列表
        print("\n[步骤2] 获取表列表...")
        adapter = SQLDialectFactory.get_adapter(db_type)
        table_names = []
        
        try:
            with engine.connect() as conn:
                if db_type == "sqlite":
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                    table_names = [row[0] for row in result]
                elif db_type == "postgresql":
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names(schema='public')
                elif db_type == "sqlserver":
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
                elif db_type == "oracle":
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
                else:
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
            
            if not isinstance(table_names, list):
                table_names = list(table_names) if table_names else []
            
            print(f"  ✓ 获取到 {len(table_names)} 个表")
            if table_names:
                print(f"    表名: {', '.join(table_names[:5])}{'...' if len(table_names) > 5 else ''}")
            else:
                print("  ⚠ 表列表为空")
                return
        except Exception as e:
            print(f"  ✗ 获取表列表失败: {e}")
            return
        
        # 步骤3: 获取表信息
        print("\n[步骤3] 获取表信息...")
        test_table = table_names[0]
        try:
            with engine.connect() as conn:
                if db_type == "sqlite":
                    pragma_result = conn.execute(text(f"PRAGMA table_info({adapter.escape_identifier(test_table)})"))
                    columns = []
                    for row in pragma_result:
                        columns.append({
                            "name": row[1],
                            "type": row[2],
                            "nullable": row[3] == 0,
                            "primary_key": row[5] == 1
                        })
                else:
                    inspector = inspect(engine)
                    columns = inspector.get_columns(test_table)
                    pk_constraint = inspector.get_pk_constraint(test_table)
                    primary_keys = pk_constraint.get('constrained_columns', []) if pk_constraint else []
            
            print(f"  ✓ 获取表 '{test_table}' 的信息成功")
            print(f"    字段数: {len(columns)}")
            if db_type != "sqlite":
                print(f"    主键: {', '.join(primary_keys) if primary_keys else '无'}")
        except Exception as e:
            print(f"  ✗ 获取表信息失败: {e}")
            return
        
        # 步骤4: 测试SQL执行（简单查询）
        print("\n[步骤4] 测试SQL执行...")
        try:
            # 构建简单查询
            if db_type == "sqlite":
                test_sql = f"SELECT * FROM {adapter.escape_identifier(test_table)} LIMIT 5"
            elif db_type == "sqlserver":
                test_sql = f"SELECT TOP 5 * FROM {adapter.escape_identifier(test_table)}"
            elif db_type == "oracle":
                test_sql = f"SELECT * FROM {adapter.escape_identifier(test_table)} FETCH FIRST 5 ROWS ONLY"
            else:
                test_sql = f"SELECT * FROM {adapter.escape_identifier(test_table)} LIMIT 5"
            
            with engine.connect() as conn:
                result = conn.execute(text(test_sql))
                rows = result.fetchall()
                columns = result.keys()
                
                # 测试数据序列化
                data = []
                for row in rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        # 处理特殊类型
                        if val is None:
                            row_dict[col] = None
                        elif hasattr(val, 'isoformat'):
                            row_dict[col] = val.isoformat()
                        elif hasattr(val, '__class__') and 'UUID' in str(type(val)):
                            row_dict[col] = str(val)
                        elif isinstance(val, bytes):
                            try:
                                row_dict[col] = val.decode('utf-8')
                            except:
                                import base64
                                row_dict[col] = base64.b64encode(val).decode('utf-8')
                        else:
                            try:
                                import json
                                json.dumps(val)
                                row_dict[col] = val
                            except:
                                row_dict[col] = str(val)
                    data.append(row_dict)
            
            print(f"  ✓ SQL执行成功，返回 {len(data)} 行数据")
            if data:
                print(f"    示例数据: {list(data[0].keys())[:3]}...")
        except Exception as e:
            print(f"  ✗ SQL执行失败: {e}")
            import traceback
            traceback.print_exc()
            return
        
        engine.dispose()
        
        # 总结
        print("\n" + "=" * 70)
        print("✓ 完整工作流程测试通过！")
        print("=" * 70)
        print("\n测试项目:")
        print("  ✓ 数据库连接")
        print("  ✓ 表列表获取")
        print("  ✓ 表信息获取")
        print("  ✓ SQL执行和数据序列化")
        print("\n该数据库配置可以正常使用！")
        
    except Exception as e:
        print(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python test_database_workflow.py <config_id>")
        print("示例: python test_database_workflow.py 1")
        sys.exit(1)
    
    config_id = int(sys.argv[1])
    test_complete_workflow(config_id)

