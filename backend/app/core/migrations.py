"""
数据库自动迁移模块
在应用启动时自动检查并执行所有迁移脚本，确保数据库结构完整
"""
import sys
from pathlib import Path
from typing import List, Callable
from sqlalchemy import text, inspect
from app.core.database import LocalSessionLocal, local_engine
from app.core.config import settings
from loguru import logger


def get_db_type() -> str:
    """检测数据库类型"""
    try:
        with local_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0].lower()
            if 'postgresql' in version or 'postgres' in version:
                return 'postgresql'
            else:
                return 'mysql'
    except Exception as e:
        logger.error(f"检测数据库类型失败: {e}")
        # 默认返回配置中的类型
        return settings.LOCAL_DB_TYPE.lower()


def check_column_exists(table_name: str, column_name: str, db_type: str = None) -> bool:
    """检查字段是否存在"""
    if db_type is None:
        db_type = get_db_type()
    
    db = LocalSessionLocal()
    try:
        if db_type == 'postgresql':
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                AND table_name = :table_name 
                AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
        else:
            # MySQL
            result = db.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = :table_name 
                AND COLUMN_NAME = :column_name
            """), {"table_name": table_name, "column_name": column_name})
        
        return result.fetchone() is not None
    except Exception as e:
        logger.error(f"检查字段 {table_name}.{column_name} 失败: {e}")
        return False
    finally:
        db.close()


def check_table_exists(table_name: str, db_type: str = None) -> bool:
    """检查表是否存在"""
    if db_type is None:
        db_type = get_db_type()
    
    try:
        inspector = inspect(local_engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.error(f"检查表 {table_name} 失败: {e}")
        return False


def run_migration_1_add_db_type_support():
    """迁移1: 添加多数据源支持（db_type和extra_params字段）"""
    db = LocalSessionLocal()
    try:
        db_type = get_db_type()
        
        # 检查并添加 db_type 字段
        if not check_column_exists('database_configs', 'db_type', db_type):
            logger.info("执行迁移: 添加 db_type 字段到 database_configs 表")
            if db_type == 'postgresql':
                db.execute(text("""
                    ALTER TABLE database_configs 
                    ADD COLUMN IF NOT EXISTS db_type VARCHAR(50) NOT NULL DEFAULT 'mysql'
                """))
            else:
                db.execute(text("""
                    ALTER TABLE database_configs 
                    ADD COLUMN db_type VARCHAR(50) NOT NULL DEFAULT 'mysql' 
                    COMMENT '数据库类型：mysql/postgresql/sqlite/sqlserver/oracle'
                """))
        
        # 检查并添加 extra_params 字段
        if not check_column_exists('database_configs', 'extra_params', db_type):
            logger.info("执行迁移: 添加 extra_params 字段到 database_configs 表")
            if db_type == 'postgresql':
                db.execute(text("""
                    ALTER TABLE database_configs 
                    ADD COLUMN IF NOT EXISTS extra_params JSONB NULL
                """))
            else:
                db.execute(text("""
                    ALTER TABLE database_configs 
                    ADD COLUMN extra_params JSON NULL 
                    COMMENT '额外连接参数（JSON格式，如SSL配置、连接池参数等）'
                """))
        
        db.commit()
        logger.info("迁移1完成: 多数据源支持")
    except Exception as e:
        db.rollback()
        logger.error(f"迁移1失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def run_migration_2_add_scene_field():
    """迁移2: 为ai_model_configs表添加scene字段"""
    db = LocalSessionLocal()
    try:
        db_type = get_db_type()
        
        if not check_column_exists('ai_model_configs', 'scene', db_type):
            logger.info("执行迁移: 添加 scene 字段到 ai_model_configs 表")
            if db_type == 'postgresql':
                db.execute(text("""
                    ALTER TABLE ai_model_configs 
                    ADD COLUMN IF NOT EXISTS scene VARCHAR(100) NULL
                """))
            else:
                db.execute(text("""
                    ALTER TABLE ai_model_configs 
                    ADD COLUMN scene VARCHAR(100) NULL 
                    COMMENT '应用场景（general/multimodal/code/math/agent/long_context/low_cost/enterprise/education/medical/legal/finance/government/industry/social/roleplay）'
                """))
            
            # 为现有记录设置默认场景值
            db.execute(text("""
                UPDATE ai_model_configs 
                SET scene = 'general' 
                WHERE scene IS NULL
            """))
        
        db.commit()
        logger.info("迁移2完成: scene字段")
    except Exception as e:
        db.rollback()
        logger.error(f"迁移2失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def run_migration_3_add_recommended_questions():
    """迁移3: 为chat_messages表添加recommended_questions字段"""
    db = LocalSessionLocal()
    try:
        db_type = get_db_type()
        
        if not check_column_exists('chat_messages', 'recommended_questions', db_type):
            logger.info("执行迁移: 添加 recommended_questions 字段到 chat_messages 表")
            if db_type == 'postgresql':
                db.execute(text("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN IF NOT EXISTS recommended_questions TEXT NULL
                """))
            else:
                db.execute(text("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN recommended_questions TEXT NULL 
                    COMMENT '推荐问题（JSON格式）'
                """))
        
        db.commit()
        logger.info("迁移3完成: recommended_questions字段")
    except Exception as e:
        db.rollback()
        logger.error(f"迁移3失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def run_migration_4_add_soft_delete():
    """迁移4: 为所有表添加is_deleted字段（软删除）"""
    db = LocalSessionLocal()
    try:
        db_type = get_db_type()
        
        # 需要添加软删除字段的表列表
        tables = [
            'database_configs',
            'interface_configs',
            'interface_parameters',
            'interface_headers',
            'ai_model_configs',
            'terminologies',
            'sql_examples',
            'custom_prompts',
            'business_knowledge',
            'chat_sessions',
            'dashboards',
            'dashboard_widgets',
            'probe_tasks'
        ]
        
        for table_name in tables:
            if not check_table_exists(table_name, db_type):
                continue  # 表不存在，跳过
            
            if not check_column_exists(table_name, 'is_deleted', db_type):
                logger.info(f"执行迁移: 添加 is_deleted 字段到 {table_name} 表")
                if db_type == 'postgresql':
                    db.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE
                    """))
                else:
                    db.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE 
                        COMMENT '是否已删除（软删除）'
                    """))
        
        db.commit()
        logger.info("迁移4完成: 软删除字段")
    except Exception as e:
        db.rollback()
        logger.error(f"迁移4失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


# 所有迁移函数列表（按执行顺序）
MIGRATIONS: List[Callable[[], None]] = [
    run_migration_1_add_db_type_support,
    run_migration_2_add_scene_field,
    run_migration_3_add_recommended_questions,
    run_migration_4_add_soft_delete,
]


def run_all_migrations():
    """执行所有迁移"""
    logger.info("=" * 50)
    logger.info("开始执行数据库自动迁移...")
    logger.info("=" * 50)
    
    try:
        # 检查数据库连接
        with local_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 执行所有迁移
        for i, migration_func in enumerate(MIGRATIONS, 1):
            try:
                logger.info(f"执行迁移 {i}/{len(MIGRATIONS)}: {migration_func.__name__}")
                migration_func()
            except Exception as e:
                logger.error(f"迁移 {i} 执行失败: {e}", exc_info=True)
                # 继续执行其他迁移，不中断
        
        logger.info("=" * 50)
        logger.info("数据库自动迁移完成")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"数据库迁移过程出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    """直接运行脚本执行迁移"""
    run_all_migrations()
