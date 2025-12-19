"""
Pytest配置文件
提供测试fixtures
"""
import pytest
from sqlalchemy.orm import Session
from app.core.database import get_local_db, Base, engine


@pytest.fixture(scope="session")
def db_session():
    """数据库会话fixture"""
    # 创建测试数据库表
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_local_db())
    
    yield db
    
    # 清理（如果需要）
    db.close()


@pytest.fixture(autouse=True)
def setup_test_db(db_session: Session):
    """每个测试前的设置"""
    # 可以在这里添加测试数据
    yield
    # 测试后清理（如果需要）
    pass

