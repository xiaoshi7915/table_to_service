"""
测试 CocoIndex Flow 的实际用法
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cocoindex import flow
    from cocoindex.sources import Postgres as PostgresSource
    from cocoindex.targets import Postgres as PostgresTarget
    from cocoindex.setting import DatabaseConnectionSpec
    
    print("=" * 60)
    print("测试 CocoIndex Flow API")
    print("=" * 60)
    
    # 测试 1: 创建简单的 Flow
    print("\n1. 测试创建 Flow...")
    try:
        @flow(name='test_flow')
        def test_flow(builder):
            print(f"  Flow builder 类型: {type(builder)}")
            print(f"  Flow builder 方法: {[m for m in dir(builder) if not m.startswith('_')]}")
            return builder
        
        print("  ✅ Flow 创建成功")
    except Exception as e:
        print(f"  ❌ Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 2: 创建带 Source 的 Flow
    print("\n2. 测试创建带 Source 的 Flow...")
    try:
        @flow(name='test_source_flow')
        def test_source_flow(builder):
            # 创建数据库连接配置
            db_config = DatabaseConnectionSpec(
                host="localhost",
                port=5432,
                database="test_db",
                user="test_user",
                password="test_pass"
            )
            
            # 添加 PostgreSQL Source
            source = builder.add_source(
                PostgresSource(
                    table_name="test_table",
                    database=db_config
                )
            )
            print(f"  ✅ Source 添加成功: {type(source)}")
            return builder
        
        print("  ✅ 带 Source 的 Flow 创建成功")
    except Exception as e:
        print(f"  ❌ 带 Source 的 Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 3: 创建完整的 Flow (Source -> Transform -> Target)
    print("\n3. 测试创建完整的 Flow...")
    try:
        @flow(name='test_full_flow')
        def test_full_flow(builder):
            # 添加 Source
            source = builder.add_source(
                PostgresSource(table_name="test_table")
            )
            
            # 添加 Target
            target = builder.add_target(
                PostgresTarget(table_name="test_target")
            )
            
            # 导出 Source 到 Target
            builder.export(source, target)
            
            print(f"  ✅ 完整 Flow 创建成功")
            return builder
        
        print("  ✅ 完整 Flow 创建成功")
    except Exception as e:
        print(f"  ❌ 完整 Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装 cocoindex: pip install cocoindex")

