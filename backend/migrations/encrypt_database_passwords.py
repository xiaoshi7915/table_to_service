"""
数据库迁移脚本：加密现有数据库配置的明文密码
"""
from sqlalchemy import text
from app.core.database import LocalSessionLocal
from app.core.password_encryption import encrypt_password, is_encrypted
from loguru import logger


def upgrade():
    """执行迁移：加密所有明文密码"""
    db = LocalSessionLocal()
    try:
        logger.info("开始加密数据库配置中的明文密码...")
        
        # 查询所有数据库配置
        result = db.execute(text("SELECT id, password FROM database_configs WHERE password IS NOT NULL AND password != ''"))
        configs = result.fetchall()
        
        encrypted_count = 0
        skipped_count = 0
        
        for config_id, password in configs:
            try:
                # 检查密码是否已加密
                if is_encrypted(password):
                    logger.debug(f"配置 {config_id} 的密码已加密，跳过")
                    skipped_count += 1
                    continue
                
                # 加密密码
                encrypted_password = encrypt_password(password)
                
                # 更新数据库
                db.execute(
                    text("UPDATE database_configs SET password = :encrypted_password WHERE id = :config_id"),
                    {"encrypted_password": encrypted_password, "config_id": config_id}
                )
                
                encrypted_count += 1
                logger.debug(f"配置 {config_id} 的密码已加密")
                
            except Exception as e:
                logger.error(f"加密配置 {config_id} 的密码失败: {e}", exc_info=True)
                continue
        
        db.commit()
        logger.info(f"迁移完成：加密了 {encrypted_count} 个密码，跳过了 {skipped_count} 个已加密的密码")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """回滚迁移：无法回滚（密码加密是单向的，但解密函数可以处理旧数据）"""
    logger.warning("密码加密迁移无法回滚，但系统会自动处理旧数据（兼容明文密码）")
    logger.info("如果需要恢复明文密码，需要手动更新数据库")


if __name__ == "__main__":
    """直接运行脚本执行迁移"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()


