"""
数据库迁移脚本：创建探查相关表
创建probe_tasks, probe_database_results, probe_table_results, probe_column_results表
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
    """执行迁移：创建探查相关表"""
    db = LocalSessionLocal()
    try:
        # 检查表是否已存在
        inspector = db.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'probe_tasks'
        """))
        
        if inspector.fetchone():
            logger.info("探查相关表已存在，跳过迁移")
            return
        
        # 创建probe_tasks表
        logger.info("创建 probe_tasks 表...")
        db.execute(text("""
            CREATE TABLE probe_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                database_config_id INT NOT NULL,
                task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
                probe_mode VARCHAR(20) NOT NULL DEFAULT 'basic' COMMENT '探查方式：basic/advanced',
                probe_level VARCHAR(20) NOT NULL DEFAULT 'database' COMMENT '探查级别：database/table/column',
                scheduling_type VARCHAR(20) NOT NULL DEFAULT 'manual' COMMENT '调度类型：manual/cron',
                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed/stopped',
                progress INT DEFAULT 0 COMMENT '进度（0-100）',
                start_time DATETIME NULL COMMENT '开始时间',
                end_time DATETIME NULL COMMENT '结束时间',
                last_probe_time DATETIME NULL COMMENT '上次探查时间',
                error_message TEXT NULL COMMENT '错误信息',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_user_id (user_id),
                INDEX idx_database_config_id (database_config_id),
                INDEX idx_status (status),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (database_config_id) REFERENCES database_configs(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='探查任务表'
        """))
        
        # 创建probe_database_results表
        logger.info("创建 probe_database_results 表...")
        db.execute(text("""
            CREATE TABLE probe_database_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                database_name VARCHAR(200) NOT NULL COMMENT '数据库名',
                db_type VARCHAR(50) NOT NULL COMMENT '数据库类型',
                total_size_mb VARCHAR(50) NULL COMMENT '总大小（MB）',
                growth_rate VARCHAR(50) NULL COMMENT '增长速率',
                table_count INT DEFAULT 0 COMMENT '表数量',
                view_count INT DEFAULT 0 COMMENT '视图数量',
                function_count INT DEFAULT 0 COMMENT '函数数量',
                procedure_count INT DEFAULT 0 COMMENT '存储过程数量',
                trigger_count INT DEFAULT 0 COMMENT '触发器数量',
                event_count INT DEFAULT 0 COMMENT '事件数量（MySQL）',
                sequence_count INT DEFAULT 0 COMMENT '序列数量（PostgreSQL）',
                top_n_tables JSON NULL COMMENT 'TOP N大表（JSON格式）',
                cold_tables JSON NULL COMMENT '冷表列表（JSON格式）',
                hot_tables JSON NULL COMMENT '热表列表（JSON格式）',
                high_risk_accounts JSON NULL COMMENT '高危账号列表（JSON格式）',
                permission_summary JSON NULL COMMENT '权限摘要（JSON格式）',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_task_id (task_id),
                INDEX idx_database_name (database_name),
                FOREIGN KEY (task_id) REFERENCES probe_tasks(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库级探查结果表'
        """))
        
        # 创建probe_table_results表
        logger.info("创建 probe_table_results 表...")
        db.execute(text("""
            CREATE TABLE probe_table_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                database_name VARCHAR(200) NOT NULL COMMENT '数据库名',
                table_name VARCHAR(200) NOT NULL COMMENT '表名',
                schema_name VARCHAR(200) NULL COMMENT 'Schema名（PostgreSQL）',
                row_count INT NULL COMMENT '行数',
                table_size_mb VARCHAR(50) NULL COMMENT '表大小（MB）',
                index_size_mb VARCHAR(50) NULL COMMENT '索引大小（MB）',
                avg_row_length VARCHAR(50) NULL COMMENT '平均行长度',
                fragmentation_rate VARCHAR(50) NULL COMMENT '碎片率',
                auto_increment_usage JSON NULL COMMENT '自增ID使用率（JSON格式）',
                column_count INT DEFAULT 0 COMMENT '字段数',
                primary_key JSON NULL COMMENT '主键（JSON格式）',
                indexes JSON NULL COMMENT '索引信息（JSON格式）',
                foreign_keys JSON NULL COMMENT '外键信息（JSON格式）',
                constraints JSON NULL COMMENT '约束信息（JSON格式）',
                partition_info JSON NULL COMMENT '分区信息（JSON格式，如果是分区表）',
                is_cold_table BOOLEAN DEFAULT FALSE COMMENT '是否冷表',
                is_hot_table BOOLEAN DEFAULT FALSE COMMENT '是否热表',
                last_access_time DATETIME NULL COMMENT '最后访问时间',
                is_hidden BOOLEAN DEFAULT FALSE COMMENT '是否屏蔽',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_task_id (task_id),
                INDEX idx_database_name (database_name),
                INDEX idx_table_name (table_name),
                INDEX idx_is_hidden (is_hidden),
                FOREIGN KEY (task_id) REFERENCES probe_tasks(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表级探查结果表'
        """))
        
        # 创建probe_column_results表
        logger.info("创建 probe_column_results 表...")
        db.execute(text("""
            CREATE TABLE probe_column_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                table_result_id INT NULL COMMENT '表结果ID',
                database_name VARCHAR(200) NOT NULL COMMENT '数据库名',
                table_name VARCHAR(200) NOT NULL COMMENT '表名',
                column_name VARCHAR(200) NOT NULL COMMENT '字段名',
                data_type VARCHAR(100) NOT NULL COMMENT '数据类型',
                nullable BOOLEAN DEFAULT TRUE COMMENT '是否可空',
                default_value TEXT NULL COMMENT '默认值',
                comment TEXT NULL COMMENT '注释',
                non_null_rate VARCHAR(50) NULL COMMENT '非空率',
                distinct_count INT NULL COMMENT '唯一值个数',
                duplicate_rate VARCHAR(50) NULL COMMENT '重复率',
                max_length INT NULL COMMENT '最大长度（字符串类型）',
                min_length INT NULL COMMENT '最小长度（字符串类型）',
                avg_length VARCHAR(50) NULL COMMENT '平均长度（字符串类型）',
                max_value VARCHAR(200) NULL COMMENT '最大值（数值/日期类型）',
                min_value VARCHAR(200) NULL COMMENT '最小值（数值/日期类型）',
                top_values JSON NULL COMMENT 'Top 20高频值（JSON格式）',
                low_frequency_values JSON NULL COMMENT '低频长尾值（JSON格式）',
                enum_values JSON NULL COMMENT '枚举值清单（JSON格式）',
                zero_count INT NULL COMMENT '零值数量（数值类型）',
                negative_count INT NULL COMMENT '负值数量（数值类型）',
                percentiles JSON NULL COMMENT '分位数（P25/P50/P75/P95/P99，JSON格式）',
                date_range JSON NULL COMMENT '日期范围（JSON格式，日期类型）',
                missing_rate VARCHAR(50) NULL COMMENT '缺失率',
                data_quality_issues JSON NULL COMMENT '数据质量问题（JSON格式）',
                sensitive_info JSON NULL COMMENT '敏感信息标识（JSON格式）',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_task_id (task_id),
                INDEX idx_table_result_id (table_result_id),
                INDEX idx_database_name (database_name),
                INDEX idx_table_name (table_name),
                INDEX idx_column_name (column_name),
                FOREIGN KEY (task_id) REFERENCES probe_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (table_result_id) REFERENCES probe_table_results(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='列级探查结果表'
        """))
        
        db.commit()
        logger.info("迁移完成：成功创建探查相关表")
        
    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """回滚迁移：删除探查相关表"""
    db = LocalSessionLocal()
    try:
        logger.info("回滚迁移：删除探查相关表...")
        
        # 删除表（按依赖关系顺序）
        db.execute(text("DROP TABLE IF EXISTS probe_column_results"))
        db.execute(text("DROP TABLE IF EXISTS probe_table_results"))
        db.execute(text("DROP TABLE IF EXISTS probe_database_results"))
        db.execute(text("DROP TABLE IF EXISTS probe_tasks"))
        
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

