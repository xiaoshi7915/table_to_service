#!/usr/bin/env python3
"""
测试Redis连接和缓存功能
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.core.cache import get_cache_service
    from app.core.config import settings
    
    print("=" * 50)
    print("Redis缓存测试")
    print("=" * 50)
    
    # 显示配置
    print(f"\n📋 Redis配置:")
    print(f"  REDIS_URL: {getattr(settings, 'REDIS_URL', '未配置')}")
    print(f"  CACHE_TTL: {getattr(settings, 'CACHE_TTL', 3600)}秒")
    
    # 获取缓存服务
    print(f"\n🔧 初始化缓存服务...")
    cache = get_cache_service()
    
    # 测试写入
    print(f"\n📝 测试写入缓存...")
    test_data = {"test": "value", "timestamp": "2025-01-01 12:00:00", "number": 12345}
    cache.set("test_key", test_data, ttl=60)
    print(f"  ✅ 写入成功: test_key")
    
    # 测试读取
    print(f"\n📖 测试读取缓存...")
    result = cache.get("test_key")
    if result:
        print(f"  ✅ 读取成功")
        print(f"  数据: {result}")
        if result.get("test") == "value":
            print(f"  ✅ 数据验证通过")
        else:
            print(f"  ❌ 数据验证失败")
    else:
        print(f"  ❌ 读取失败")
    
    # 测试删除
    print(f"\n🗑️  测试删除缓存...")
    cache.delete("test_key")
    result_after_delete = cache.get("test_key")
    if result_after_delete is None:
        print(f"  ✅ 删除成功")
    else:
        print(f"  ❌ 删除失败")
    
    # 检查缓存后端类型
    print(f"\n🔍 缓存后端信息:")
    if cache.redis_client:
        print(f"  ✅ 使用Redis作为缓存后端")
        try:
            info = cache.redis_client.info("server")
            print(f"  Redis版本: {info.get('redis_version', '未知')}")
        except:
            pass
    else:
        print(f"  ⚠️  使用内存缓存（Redis未配置或不可用）")
    
    print(f"\n" + "=" * 50)
    print("✅ Redis缓存测试完成")
    print("=" * 50)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装redis库: pip install redis")
    sys.exit(1)
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
