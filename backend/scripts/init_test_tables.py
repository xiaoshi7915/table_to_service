"""
初始化测试数据库表
创建测试用例需要的表和数据
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from app.core.database import get_local_db
from app.models import DatabaseConfig


def create_test_tables(db_config: DatabaseConfig):
    """
    创建测试表
    
    Args:
        db_config: 数据库配置
    """
    from app.core.db_factory import DatabaseConnectionFactory
    
    engine = DatabaseConnectionFactory.create_engine(db_config)
    
    try:
        with engine.connect() as conn:
            # 检查并创建/更新用户表
            # 先检查表是否存在
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'users'
            """))
            table_exists = result.fetchone()[0] > 0
            
            if not table_exists:
                # 创建新表
                conn.execute(text("""
                    CREATE TABLE users (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            else:
                # 检查字段是否存在，不存在则添加
                result = conn.execute(text("""
                    SELECT COUNT(*) as cnt FROM information_schema.columns 
                    WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'email'
                """))
                has_email = result.fetchone()[0] > 0
                
                if not has_email:
                    conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE"))
                
                result = conn.execute(text("""
                    SELECT COUNT(*) as cnt FROM information_schema.columns 
                    WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'created_at'
                """))
                has_created_at = result.fetchone()[0] > 0
                
                if not has_created_at:
                    conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            
            # 清空并插入测试数据
            conn.execute(text("DELETE FROM users WHERE id IN (1, 2, 3)"))
            conn.execute(text("""
                INSERT INTO users (id, name, email) VALUES
                (1, '张三', 'zhangsan@example.com'),
                (2, '李四', 'lisi@example.com'),
                (3, '王五', 'wangwu@example.com')
            """))
            
            # 2. 部门表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'departments'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE departments (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description TEXT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM departments WHERE id IN (1, 2, 3)"))
            conn.execute(text("""
                INSERT INTO departments (id, name, description) VALUES
                (1, '技术部', '负责技术开发'),
                (2, '销售部', '负责产品销售'),
                (3, '市场部', '负责市场推广')
            """))
            
            # 3. 员工表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'employees'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE employees (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        department_id INT,
                        salary DECIMAL(10, 2),
                        hire_date DATE,
                        FOREIGN KEY (department_id) REFERENCES departments(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM employees WHERE id IN (1, 2, 3, 4, 5)"))
            conn.execute(text("""
                INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES
                (1, '员工A', 1, 10000.00, '2023-01-01'),
                (2, '员工B', 1, 12000.00, '2023-02-01'),
                (3, '员工C', 2, 8000.00, '2023-03-01'),
                (4, '员工D', 2, 9000.00, '2023-04-01'),
                (5, '员工E', 3, 7500.00, '2023-05-01')
            """))
            
            # 4. 产品表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'products'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE products (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        price DECIMAL(10, 2),
                        category VARCHAR(50)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM products WHERE id IN (1, 2, 3, 4, 5)"))
            conn.execute(text("""
                INSERT INTO products (id, name, price, category) VALUES
                (1, '产品A', 100.00, '电子产品'),
                (2, '产品B', 200.00, '电子产品'),
                (3, '产品C', 150.00, '日用品'),
                (4, '产品D', 300.00, '电子产品'),
                (5, '产品E', 80.00, '日用品')
            """))
            
            # 5. 销售表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'sales'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE sales (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        product_id INT,
                        amount DECIMAL(10, 2),
                        sale_date DATE,
                        region VARCHAR(50),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM sales WHERE id BETWEEN 1 AND 10"))
            conn.execute(text("""
                INSERT INTO sales (id, product_id, amount, sale_date, region) VALUES
                (1, 1, 1000.00, '2024-01-15', '华东'),
                (2, 2, 2000.00, '2024-01-16', '华南'),
                (3, 1, 1500.00, '2024-01-17', '华东'),
                (4, 3, 1200.00, '2024-01-18', '华北'),
                (5, 2, 2500.00, '2024-01-19', '华南'),
                (6, 4, 3000.00, '2024-01-20', '华东'),
                (7, 5, 800.00, '2024-01-21', '华北'),
                (8, 1, 1100.00, '2024-01-22', '华南'),
                (9, 3, 1300.00, '2024-01-23', '华东'),
                (10, 2, 2200.00, '2024-01-24', '华南')
            """))
            
            # 6. 客户表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'customers'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE customers (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(255),
                        phone VARCHAR(20)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM customers WHERE id IN (1, 2, 3)"))
            conn.execute(text("""
                INSERT INTO customers (id, name, email, phone) VALUES
                (1, '客户A', 'customer_a@example.com', '13800138001'),
                (2, '客户B', 'customer_b@example.com', '13800138002'),
                (3, '客户C', 'customer_c@example.com', '13800138003')
            """))
            
            # 7. 订单表
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'orders'
            """))
            if result.fetchone()[0] == 0:
                conn.execute(text("""
                    CREATE TABLE orders (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        customer_id INT,
                        order_date DATE,
                        total_amount DECIMAL(10, 2),
                        status VARCHAR(20),
                        FOREIGN KEY (customer_id) REFERENCES customers(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
            
            conn.execute(text("DELETE FROM orders WHERE id BETWEEN 1 AND 6"))
            conn.execute(text("""
                INSERT INTO orders (id, customer_id, order_date, total_amount, status) VALUES
                (1, 1, '2024-01-05', 500.00, '已完成'),
                (2, 1, '2024-01-10', 800.00, '已完成'),
                (3, 2, '2024-01-15', 1200.00, '已完成'),
                (4, 2, '2024-01-20', 600.00, '已完成'),
                (5, 3, '2024-01-25', 900.00, '已完成'),
                (6, 3, '2024-01-30', 1500.00, '已完成')
            """))
            
            conn.commit()
            logger.info("测试表创建成功")
            
    except Exception as e:
        logger.error(f"创建测试表失败: {e}", exc_info=True)
        raise
    finally:
        engine.dispose()


def main():
    """主函数"""
    db = next(get_local_db())
    
    try:
        # 获取第一个激活的数据库配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.is_active == True
        ).first()
        
        if not db_config:
            logger.error("未找到激活的数据库配置")
            return
        
        logger.info(f"使用数据库配置: {db_config.name} ({db_config.db_type})")
        
        # 创建测试表
        create_test_tables(db_config)
        
        logger.info("测试数据初始化完成")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()

