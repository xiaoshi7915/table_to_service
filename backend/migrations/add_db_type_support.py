"""
数据库迁移脚本：添加多数据源支持
为database_configs表添加db_type和extra_params字段
"""
from sqlalchemy import text
from app.core.database import LocalSessionLocal
from loguru import logger


def upgrade():
    """执行迁移：添加db_type和extra_params字段"""
    db = LocalSessionLocal()
    try:
        # 检查字段是否已存在
        inspector = db.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'database_configs' 
            AND COLUMN_NAME = 'db_type'
        """))
        
        if inspector.fetchone():
            logger.info("字段 db_type 已存在，跳过迁移")
            return
        
        # 添加db_type字段（默认值为mysql，保持向后兼容）
        logger.info("添加 db_type 字段...")
        db.execute(text("""
            ALTER TABLE database_configs 
            ADD COLUMN db_type VARCHAR(50) NOT NULL DEFAULT 'mysql' 
            COMMENT '数据库类型：mysql/postgresql/sqlite/sqlserver/oracle'
            AFTER name
        """))
        
        # 添加extra_params字段（JSON类型，用于存储额外连接参数）
        logger.info("添加 extra_params 字段...")
        db.execute(text("""
            ALTER TABLE database_configs 
            ADD COLUMN extra_params JSON NULL 
            COMMENT '额外连接参数（JSON格式，如SSL配置、连接池参数等）'
            AFTER charset
        """))
        
        # 为现有数据设置默认值（虽然已经有DEFAULT，但为了确保数据一致性）
        logger.info("更新现有数据的db_type为mysql...")
        db.execute(text("""
            UPDATE database_configs 
            SET db_type = 'mysql' 
            WHERE db_type IS NULL OR db_type = ''
        """))
        
        db.commit()
        logger.info("迁移完成：成功添加db_type和extra_params字段")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """回滚迁移：删除db_type和extra_params字段"""
    db = LocalSessionLocal()
    try:
        logger.info("回滚迁移：删除db_type和extra_params字段...")
        
        # 删除extra_params字段
        db.execute(text("ALTER TABLE database_configs DROP COLUMN extra_params"))
        
        # 删除db_type字段
        db.execute(text("ALTER TABLE database_configs DROP COLUMN db_type"))
        
        db.commit()
        logger.info("回滚完成")
        
    except Exception as e:
        db.rollback()
        logger.error(f"回滚失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    """直接运行脚本执行迁移"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()

