"""
初始化pgvector扩展
在PostgreSQL数据库中创建pgvector扩展和向量表
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from loguru import logger
from app.core.config import settings


def init_pgvector():
    """初始化pgvector扩展"""
    logger.info("开始初始化pgvector扩展...")
    
    # 使用本地数据库连接（PostgreSQL）
    # 注意：需要确保LOCAL_DB配置的是PostgreSQL数据库
    connection_string = settings.local_database_url
    
    # 检查是否是PostgreSQL
    if "postgresql" not in connection_string.lower():
        logger.error("pgvector需要PostgreSQL数据库，当前配置不是PostgreSQL")
        logger.info(f"当前数据库URL: {connection_string}")
        logger.info("请将LOCAL_DB配置为PostgreSQL数据库")
        return False
    
    try:
        # 创建引擎
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # 1. 创建pgvector扩展
            logger.info("创建pgvector扩展...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("✓ pgvector扩展创建成功")
            
            # 2. 创建术语库向量表
            logger.info("创建术语库向量表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS terminology_embeddings (
                    id SERIAL PRIMARY KEY,
                    terminology_id INTEGER,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 创建索引
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS terminology_embeddings_vector_idx 
                ON terminology_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            
            conn.commit()
            logger.info("✓ 术语库向量表创建成功")
            
            # 3. 创建SQL示例向量表
            logger.info("创建SQL示例向量表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sql_example_embeddings (
                    id SERIAL PRIMARY KEY,
                    example_id INTEGER,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS sql_example_embeddings_vector_idx 
                ON sql_example_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            
            conn.commit()
            logger.info("✓ SQL示例向量表创建成功")
            
            # 4. 创建知识库向量表
            logger.info("创建知识库向量表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS knowledge_chunk_embeddings (
                    id SERIAL PRIMARY KEY,
                    chunk_id INTEGER,
                    knowledge_id INTEGER,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS knowledge_chunk_embeddings_vector_idx 
                ON knowledge_chunk_embeddings 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            
            conn.commit()
            logger.info("✓ 知识库向量表创建成功")
            
            logger.info("=" * 50)
            logger.info("pgvector扩展初始化完成！")
            logger.info("=" * 50)
            
            return True
            
    except Exception as e:
        logger.error(f"初始化pgvector失败: {e}", exc_info=True)
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        success = init_pgvector()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


