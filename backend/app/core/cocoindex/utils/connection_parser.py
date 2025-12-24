"""
数据库连接字符串解析器
将连接字符串解析为 CocoIndex DatabaseConnectionSpec
"""
from typing import Optional
from loguru import logger

try:
    from cocoindex.setting import DatabaseConnectionSpec
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False
    DatabaseConnectionSpec = None


def parse_connection_string(connection_string: str) -> Optional[DatabaseConnectionSpec]:
    """
    解析 PostgreSQL 连接字符串
    
    Args:
        connection_string: 连接字符串，格式如 postgresql://user:pass@host:port/dbname
        
    Returns:
        DatabaseConnectionSpec 对象，如果解析失败返回 None
    """
    if not COCOINDEX_AVAILABLE:
        logger.warning("cocoindex 未安装，无法创建 DatabaseConnectionSpec")
        return None
    
    try:
        # DatabaseConnectionSpec 只需要 url 参数（连接字符串）
        # 以及可选的 user, password, max_connections, min_connections
        
        # 解析 URL 提取用户名和密码（如果需要单独传递）
        from urllib.parse import urlparse
        parsed = urlparse(connection_string)
        username = parsed.username
        password = parsed.password
        
        # 创建 DatabaseConnectionSpec
        # 注意：DatabaseConnectionSpec 使用 url 参数，不是 host/port/database
        # url 参数是必需的，user 和 password 是可选的
        db_spec = DatabaseConnectionSpec(
            url=connection_string,  # 直接使用连接字符串（必需）
            user=username if username else None,  # 可选
            password=password if password else None  # 可选
        )
        
        logger.debug(f"连接字符串解析成功: {connection_string[:50]}...")
        return db_spec
    except Exception as e:
        logger.error(f"解析连接字符串失败: {e}")
        import traceback
        traceback.print_exc()
        return None
