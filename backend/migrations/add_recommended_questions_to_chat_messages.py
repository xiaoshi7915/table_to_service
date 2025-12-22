"""
数据库迁移脚本：为 chat_messages 表添加 recommended_questions 字段
用于存储AI生成的推荐问题（JSON格式）
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app.core.database import LocalSessionLocal
from loguru import logger


def upgrade():
    """执行迁移：添加 recommended_questions 字段"""
    db = LocalSessionLocal()
    try:
        # 检测数据库类型
        db_type_result = db.execute(text("SELECT version()"))
        db_version = db_type_result.fetchone()[0].lower()
        
        is_postgresql = 'postgresql' in db_version or 'postgres' in db_version
        
        # 检查字段是否已存在
        if is_postgresql:
            # PostgreSQL
            inspector = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                AND table_name = 'chat_messages' 
                AND column_name = 'recommended_questions'
            """))
        else:
            # MySQL
            inspector = db.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'chat_messages' 
                AND COLUMN_NAME = 'recommended_questions'
            """))
        
        if inspector.fetchone():
            logger.info("字段 recommended_questions 已存在，跳过迁移")
            return
        
        # 添加 recommended_questions 字段
        logger.info("添加 recommended_questions 字段...")
        if is_postgresql:
            # PostgreSQL
            db.execute(text("""
                ALTER TABLE chat_messages 
                ADD COLUMN recommended_questions TEXT NULL
            """))
        else:
            # MySQL
            db.execute(text("""
                ALTER TABLE chat_messages 
                ADD COLUMN recommended_questions TEXT NULL 
                COMMENT '推荐问题（JSON格式）'
                AFTER response_time
            """))
        
        db.commit()
        logger.info("迁移完成：成功添加 recommended_questions 字段")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """回滚迁移：删除 recommended_questions 字段"""
    db = LocalSessionLocal()
    try:
        # 检测数据库类型
        db_type_result = db.execute(text("SELECT version()"))
        db_version = db_type_result.fetchone()[0].lower()
        
        is_postgresql = 'postgresql' in db_version or 'postgres' in db_version
        
        # 检查字段是否存在
        if is_postgresql:
            # PostgreSQL
            inspector = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                AND table_name = 'chat_messages' 
                AND column_name = 'recommended_questions'
            """))
        else:
            # MySQL
            inspector = db.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'chat_messages' 
                AND COLUMN_NAME = 'recommended_questions'
            """))
        
        if not inspector.fetchone():
            logger.info("字段 recommended_questions 不存在，跳过回滚")
            return
        
        # 删除字段
        logger.info("删除 recommended_questions 字段...")
        db.execute(text("""
            ALTER TABLE chat_messages 
            DROP COLUMN recommended_questions
        """))
        
        db.commit()
        logger.info("回滚完成：成功删除 recommended_questions 字段")
        
    except Exception as e:
        db.rollback()
        logger.error(f"回滚失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()

