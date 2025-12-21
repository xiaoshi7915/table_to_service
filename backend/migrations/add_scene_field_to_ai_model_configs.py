"""
数据库迁移脚本：为ai_model_configs表添加scene字段
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app.core.database import LocalSessionLocal, engine
from loguru import logger


def upgrade():
    """添加scene字段"""
    db = LocalSessionLocal()
    
    try:
        # 检查数据库类型
        from app.core.config import settings
        db_type = settings.LOCAL_DB_TYPE.lower()
        
        if db_type == "postgresql":
            # PostgreSQL
            db.execute(text("""
                ALTER TABLE ai_model_configs 
                ADD COLUMN IF NOT EXISTS scene VARCHAR(100) NULL
            """))
            logger.info("PostgreSQL: 已添加scene字段到ai_model_configs表")
        else:
            # MySQL
            # 检查字段是否已存在
            result = db.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'ai_model_configs'
                AND COLUMN_NAME = 'scene'
            """))
            count = result.fetchone()[0]
            
            if count == 0:
                db.execute(text("""
                    ALTER TABLE ai_model_configs 
                    ADD COLUMN scene VARCHAR(100) NULL COMMENT '应用场景（general/multimodal/code/math/agent/long_context/low_cost/enterprise/education/medical/legal/finance/government/industry/social/roleplay）'
                """))
                logger.info("MySQL: 已添加scene字段到ai_model_configs表")
            else:
                logger.info("MySQL: scene字段已存在，跳过")
        
        # 为现有记录设置默认场景值
        db.execute(text("""
            UPDATE ai_model_configs 
            SET scene = 'general' 
            WHERE scene IS NULL
        """))
        
        db.commit()
        logger.info("迁移完成：已为现有记录设置默认场景值")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """移除scene字段"""
    db = LocalSessionLocal()
    
    try:
        from app.core.config import settings
        db_type = settings.LOCAL_DB_TYPE.lower()
        
        if db_type == "postgresql":
            db.execute(text("ALTER TABLE ai_model_configs DROP COLUMN IF EXISTS scene"))
        else:
            db.execute(text("ALTER TABLE ai_model_configs DROP COLUMN scene"))
        
        db.commit()
        logger.info("已移除scene字段")
        
    except Exception as e:
        db.rollback()
        logger.error(f"回滚失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移：添加scene字段")
    parser.add_argument("--downgrade", action="store_true", help="回滚迁移")
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade()

