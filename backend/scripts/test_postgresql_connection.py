"""
PostgreSQL 连接测试脚本
用于诊断PostgreSQL连接问题
"""
import sys
from pathlib import Path

# 添加项目路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import socket
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from loguru import logger
from app.core.config import settings


def test_network_connection(host, port, timeout=10):
    """测试网络连接"""
    logger.info(f"测试网络连接到 {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.info("✓ 网络连接成功")
            return True
        else:
            logger.error(f"✗ 网络连接失败 (错误代码: {result})")
            # 错误代码说明
            error_codes = {
                111: "连接被拒绝 - 服务未运行或端口未开放",
                113: "无路由到主机 - 网络路由问题，可能需要使用外网地址或配置VPC路由",
                110: "连接超时 - 防火墙阻止或网络延迟过高",
            }
            if result in error_codes:
                logger.error(f"错误说明: {error_codes[result]}")
            
            logger.error("可能的原因：")
            logger.error("1. PostgreSQL服务未运行")
            logger.error("2. 防火墙阻止了连接")
            logger.error("3. PostgreSQL未监听该端口")
            logger.error("4. 网络路由问题（错误113）- 如果使用内网地址，确保服务器在同一VPC；否则使用外网地址")
            logger.error("5. 白名单未正确配置 - 确保RDS白名单包含当前服务器的IP")
            return False
    except socket.gaierror as e:
        logger.error(f"✗ DNS解析失败: {e}")
        logger.error("请检查主机名或IP地址是否正确")
        return False
    except socket.timeout:
        logger.error(f"✗ 连接超时（{timeout}秒）")
        logger.error("可能的原因：")
        logger.error("1. 网络延迟过高")
        logger.error("2. 防火墙阻止了连接")
        logger.error("3. PostgreSQL服务未运行")
        return False
    except Exception as e:
        logger.error(f"✗ 网络连接测试失败: {e}")
        return False


def test_database_connection(host, port, user, password, database):
    """测试数据库连接"""
    logger.info(f"测试数据库连接: {host}:{port}/{database} (用户: {user})...")
    
    try:
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)
        url = f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{host}:{port}/{database}"
        
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 30,
                "sslmode": "prefer"
            }
        )
        
        with engine.connect() as conn:
            # 测试基本查询
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info("✓ 数据库连接成功")
            logger.info(f"PostgreSQL版本: {version[:50]}...")
            
            # 测试数据库信息
            result = conn.execute(text("SELECT current_database(), current_user"))
            db_info = result.fetchone()
            logger.info(f"当前数据库: {db_info[0]}")
            logger.info(f"当前用户: {db_info[1]}")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        logger.error("可能的原因：")
        logger.error("1. 数据库名称不存在")
        logger.error("2. 用户名或密码错误")
        logger.error("3. 用户没有访问该数据库的权限")
        logger.error("4. PostgreSQL配置不允许远程连接")
        return False
    finally:
        try:
            engine.dispose()
        except:
            pass


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("PostgreSQL 连接诊断工具")
    logger.info("=" * 60)
    
    # 从配置获取连接信息
    if settings.LOCAL_DB_TYPE.lower() == "postgresql":
        host = settings.LOCAL_DB_HOST
        port = settings.LOCAL_DB_PORT
        user = settings.LOCAL_DB_USER
        password = settings.LOCAL_DB_PASSWORD
        database = settings.LOCAL_DB_NAME
    else:
        # 从环境变量获取
        import os
        host = os.getenv("NEW_PG_HOST", "gp-bp1789ydq5950he7po-master.gpdb.rds.aliyuncs.com")
        port = int(os.getenv("NEW_PG_PORT", "5432"))
        user = os.getenv("NEW_PG_USER", "cxs_vector")
        password = os.getenv("NEW_PG_PASSWORD", "4441326cxs!!")
        database = os.getenv("NEW_PG_DB", "local_service")
    
    logger.info(f"连接信息:")
    logger.info(f"  主机: {host}")
    logger.info(f"  端口: {port}")
    logger.info(f"  用户: {user}")
    logger.info(f"  数据库: {database}")
    logger.info("")
    
    # 1. 测试网络连接
    network_ok = test_network_connection(host, port)
    logger.info("")
    
    if not network_ok:
        logger.error("=" * 60)
        logger.error("网络连接失败，无法继续测试数据库连接")
        logger.error("=" * 60)
        logger.info("")
        logger.info("排查建议：")
        logger.info("1. 检查PostgreSQL服务是否运行: systemctl status postgresql")
        logger.info("2. 检查防火墙设置: firewall-cmd --list-all 或 iptables -L")
        logger.info("3. 检查PostgreSQL配置:")
        logger.info("   - postgresql.conf: listen_addresses = '*'")
        logger.info("   - pg_hba.conf: 添加允许远程连接的规则")
        logger.info("4. 检查网络路由和DNS解析")
        return False
    
    # 2. 测试数据库连接
    db_ok = test_database_connection(host, port, user, password, database)
    logger.info("")
    
    if db_ok:
        logger.info("=" * 60)
        logger.info("✓ 所有连接测试通过！")
        logger.info("=" * 60)
        return True
    else:
        logger.error("=" * 60)
        logger.error("数据库连接失败")
        logger.error("=" * 60)
        logger.info("")
        logger.info("排查建议：")
        logger.info("1. 确认数据库名称存在: psql -l")
        logger.info("2. 确认用户存在且有权限:")
        logger.info(f"   CREATE USER {user} WITH PASSWORD 'your_password';")
        logger.info(f"   GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};")
        logger.info("3. 检查pg_hba.conf配置，确保允许该用户从该IP连接")
        logger.info("4. 重启PostgreSQL服务使配置生效")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)

