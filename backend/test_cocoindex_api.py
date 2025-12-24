"""
测试 CocoIndex 实际 API
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from cocoindex import flow_def
    from cocoindex.flow import FlowBuilder, DataScope
    from cocoindex.sources import Postgres as PostgresSource
    from cocoindex.targets import Postgres as PostgresTarget
    from cocoindex.setting import DatabaseConnectionSpec
    
    print("=" * 60)
    print("测试 CocoIndex 实际 API")
    print("=" * 60)
    
    # 测试 1: 使用 flow_def 装饰器创建 Flow
    print("\n1. 测试 flow_def 装饰器...")
    try:
        @flow_def(name='test_flow')
        def test_flow(builder: FlowBuilder, scope: DataScope):
            print(f"  ✅ Flow 函数接收参数: builder={type(builder)}, scope={type(scope)}")
            print(f"  ✅ Builder 方法: {[m for m in dir(builder) if not m.startswith('_') and callable(getattr(builder, m, None))][:10]}")
            return builder
        
        print("  ✅ flow_def 装饰器可用")
    except Exception as e:
        print(f"  ❌ flow_def 装饰器失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 2: 创建带 Source 的 Flow
    print("\n2. 测试创建带 Source 的 Flow...")
    try:
        @flow_def(name='test_source_flow')
        def test_source_flow(builder: FlowBuilder, scope: DataScope):
            # 添加 PostgreSQL Source
            source = builder.add_source(
                PostgresSource(
                    table_name="test_table"
                ),
                name="test_source"
            )
            print(f"  ✅ Source 添加成功: {type(source)}")
            print(f"  ✅ Source 类型: {type(source)}")
            return builder
        
        print("  ✅ 带 Source 的 Flow 创建成功")
    except Exception as e:
        print(f"  ❌ 带 Source 的 Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 3: 创建完整的 Flow (Source -> Target)
    print("\n3. 测试创建完整的 Flow (Source -> Target)...")
    try:
        @flow_def(name='test_full_flow')
        def test_full_flow(builder: FlowBuilder, scope: DataScope):
            # 添加 Source
            source = builder.add_source(
                PostgresSource(table_name="test_table"),
                name="source"
            )
            
            # 添加 Target
            target = builder.add_target(
                PostgresTarget(table_name="test_target"),
                name="target"
            )
            
            # 导出 Source 到 Target
            # 注意：需要查看实际的 export 方法
            print(f"  ✅ Source: {type(source)}")
            print(f"  ✅ Target: {type(target)}")
            
            # 尝试导出
            try:
                builder.export(source, target)
                print("  ✅ export 方法可用")
            except AttributeError:
                print("  ⚠️  builder.export 不可用，可能需要其他方式")
            
            return builder
        
        print("  ✅ 完整 Flow 创建成功")
    except Exception as e:
        print(f"  ❌ 完整 Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试 4: 查看 DataCollector 的用法
    print("\n4. 测试 DataCollector...")
    try:
        @flow_def(name='test_collector_flow')
        def test_collector_flow(builder: FlowBuilder, scope: DataScope):
            # 添加 Source
            source = builder.add_source(
                PostgresSource(table_name="test_table"),
                name="source"
            )
            
            # 创建 DataCollector
            collector = builder.collect(source)
            print(f"  ✅ Collector 创建成功: {type(collector)}")
            print(f"  ✅ Collector 方法: {[m for m in dir(collector) if not m.startswith('_') and callable(getattr(collector, m, None))]}")
            
            # 尝试导出到 Target
            try:
                target = PostgresTarget(table_name="test_target")
                collector.export(
                    target_name="target",
                    target_spec=target,
                    primary_key_fields=["id"]
                )
                print("  ✅ collector.export 可用")
            except Exception as e:
                print(f"  ⚠️  collector.export 测试失败: {e}")
            
            return builder
        
        print("  ✅ DataCollector Flow 创建成功")
    except Exception as e:
        print(f"  ❌ DataCollector Flow 创建失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

