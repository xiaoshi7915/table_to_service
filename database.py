"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from config import settings
from loguru import logger

# 创建目标数据库引擎（用于表转服务的目标数据库）
target_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,   # 1小时后回收连接
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    echo=settings.DEBUG,  # 是否打印SQL语句
    connect_args={
        "connect_timeout": 15,  # 连接超时时间（秒）- 增加到15秒
        "read_timeout": 30,    # 读取超时时间（秒）- 增加到30秒
        "write_timeout": 30,   # 写入超时时间（秒）- 增加到30秒
    }
)

# 创建本地数据库引擎（用于服务自身数据存储）
local_engine = create_engine(
    settings.local_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 10,
        "write_timeout": 10,
    }
)

# 为了向后兼容，保留 engine 作为目标数据库引擎
engine = target_engine

# 创建会话工厂
# 目标数据库会话（用于表转服务）
TargetSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

# 本地数据库会话（用于服务自身数据存储）
LocalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)

# 为了向后兼容，保留 SessionLocal 作为本地数据库会话（用户表等）
SessionLocal = LocalSessionLocal

# 创建基础模型类
Base = declarative_base()

# 元数据
metadata = MetaData()


def get_db() -> Generator[Session, None, None]:
    """
    获取本地数据库会话的依赖注入函数（用于用户表等）
    """
    db = LocalSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"本地数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_local_db() -> Generator[Session, None, None]:
    """
    获取本地数据库会话的依赖注入函数（别名，用于配置表等）
    """
    yield from get_db()


def get_target_db() -> Generator[Session, None, None]:
    """
    获取目标数据库会话的依赖注入函数（用于表转服务）
    """
    db = TargetSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"目标数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_table_names() -> list:
    """
    获取目标数据库中所有表名
    """
    try:
        inspector = inspect(target_engine)
        return inspector.get_table_names()
    except Exception as e:
        logger.error(f"获取表名失败: {e}")
        raise


def get_table_columns(table_name: str) -> list:
    """
    获取指定表的所有列信息（目标数据库）
    """
    try:
        inspector = inspect(target_engine)
        columns = inspector.get_columns(table_name)
        return columns
    except Exception as e:
        logger.error(f"获取表 {table_name} 的列信息失败: {e}")
        raise


def get_primary_key(table_name: str) -> str:
    """
    获取指定表的主键列名（目标数据库）
    """
    try:
        inspector = inspect(target_engine)
        pk_constraint = inspector.get_pk_constraint(table_name)
        if pk_constraint and pk_constraint.get('constrained_columns'):
            return pk_constraint['constrained_columns'][0]
        return None
    except Exception as e:
        logger.error(f"获取表 {table_name} 的主键失败: {e}")
        return None


def test_connection() -> bool:
    """
    测试目标数据库连接
    """
    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("目标数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"目标数据库连接失败: {e}")
        return False


def test_local_connection() -> bool:
    """
    测试本地数据库连接
    """
    try:
        with local_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("本地数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"本地数据库连接失败: {e}")
        return False

