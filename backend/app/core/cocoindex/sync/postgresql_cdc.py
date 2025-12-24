"""
PostgreSQL CDC 监听器
使用 logical replication 或 pg_notify 监听表变更
"""
from typing import Callable, Optional
from datetime import datetime
from loguru import logger
import threading
import time

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 未安装，PostgreSQL CDC 将不可用")


class PostgreSQLCDC:
    """PostgreSQL Change Data Capture 监听器"""
    
    def __init__(
        self,
        connection_string: str,
        tables: list,
        callback: Callable[[str, dict], None]
    ):
        """
        初始化 CDC 监听器
        
        Args:
            connection_string: PostgreSQL 连接字符串
            tables: 要监听的表列表
            callback: 变更回调函数，接收 (operation, record) 参数
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 未安装，请安装 psycopg2")
        
        self.connection_string = connection_string
        self.tables = tables
        self.callback = callback
        self.running = False
        self.thread = None
    
    def start(self):
        """启动 CDC 监听"""
        if self.running:
            logger.warning("CDC 监听已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        logger.info(f"PostgreSQL CDC 监听已启动，监听表: {', '.join(self.tables)}")
    
    def stop(self):
        """停止 CDC 监听"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("PostgreSQL CDC 监听已停止")
    
    def _listen(self):
        """监听循环（优先使用 pg_notify，降级到轮询）"""
        # 首先尝试使用 pg_notify 监听（需要触发器支持）
        # 如果失败，降级到轮询方式
        
        # 尝试使用 pg_notify
        try:
            self._listen_with_notify()
            return
        except Exception as e:
            logger.warning(f"pg_notify 监听失败: {e}，降级到轮询方式")
        
        # 降级到轮询方式
        self._listen_with_polling()
    
    def _listen_with_notify(self):
        """使用 pg_notify 监听变更（需要触发器支持）"""
        import select
        
        conn = psycopg2.connect(self.connection_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            # 为每个表创建监听通道
            for table in self.tables:
                channel = f"table_changes_{table}"
                cursor.execute(f"LISTEN {channel};")
                logger.info(f"开始监听通道: {channel}")
            
            # 监听通知
            while self.running:
                if select.select([conn], [], [], 5) == ([], [], []):
                    # 超时，继续循环
                    continue
                
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    try:
                        # 解析通知内容（JSON格式）
                        import json
                        payload = json.loads(notify.payload)
                        operation = payload.get("operation", "update")
                        record = payload.get("record", {})
                        
                        self.callback(operation, record)
                        logger.debug(f"收到变更通知: {operation} on {notify.channel}")
                    except Exception as e:
                        logger.error(f"处理通知失败: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def _listen_with_polling(self):
        """使用轮询方式监听变更（降级方案）"""
        
        last_check = {}
        for table in self.tables:
            last_check[table] = datetime.now()
        
        while self.running:
            try:
                conn = psycopg2.connect(self.connection_string)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = conn.cursor()
                
                for table in self.tables:
                    try:
                        # 查询最近更新的记录
                        query = f"""
                        SELECT * FROM {table}
                        WHERE updated_at > %s AND is_deleted = false
                        ORDER BY updated_at DESC
                        LIMIT 100
                        """
                        cursor.execute(query, (last_check[table],))
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        
                        for row in rows:
                            record = dict(zip(columns, row))
                            # 检查是否是新增还是更新
                            created_at = record.get('created_at')
                            updated_at = record.get('updated_at')
                            
                            if created_at and updated_at and created_at == updated_at:
                                operation = "insert"
                            else:
                                operation = "update"
                            
                            self.callback(operation, record)
                            last_check[table] = updated_at or datetime.now()
                        
                        # 查询已删除的记录（软删除）
                        delete_query = f"""
                        SELECT * FROM {table}
                        WHERE updated_at > %s AND is_deleted = true
                        ORDER BY updated_at DESC
                        LIMIT 100
                        """
                        cursor.execute(delete_query, (last_check[table],))
                        deleted_rows = cursor.fetchall()
                        
                        for row in deleted_rows:
                            record = dict(zip(columns, row))
                            self.callback("delete", record)
                            last_check[table] = record.get('updated_at') or datetime.now()
                    
                    except Exception as e:
                        logger.error(f"监听表 {table} 失败: {e}")
                        continue
                
                cursor.close()
                conn.close()
                
                # 等待一段时间再检查
                time.sleep(5)  # 5秒轮询一次
                
            except Exception as e:
                logger.error(f"CDC 监听错误: {e}")
                time.sleep(10)  # 出错后等待更长时间
    
    def _setup_logical_replication(self):
        """
        设置 logical replication（需要数据库管理员权限）
        
        注意：这是一个高级功能，需要：
        1. PostgreSQL 配置 wal_level = logical
        2. 创建 replication slot
        3. 创建 publication
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            try:
                # 检查 wal_level
                cursor.execute("SHOW wal_level;")
                wal_level = cursor.fetchone()[0]
                if wal_level != 'logical':
                    logger.warning(f"wal_level 为 {wal_level}，需要设置为 'logical'")
                    logger.info("请在 postgresql.conf 中设置: wal_level = logical")
                    return False
                
                # 创建 replication slot（如果不存在）
                slot_name = f"cocoindex_cdc_{self.tables[0] if self.tables else 'default'}"
                cursor.execute("""
                    SELECT slot_name FROM pg_replication_slots 
                    WHERE slot_name = %s;
                """, (slot_name,))
                if not cursor.fetchone():
                    cursor.execute(f"""
                        SELECT pg_create_logical_replication_slot(
                            '{slot_name}',
                            'pgoutput'
                        );
                    """)
                    logger.info(f"创建 replication slot: {slot_name}")
                
                # 创建 publication（如果不存在）
                pub_name = f"cocoindex_pub_{self.tables[0] if self.tables else 'default'}"
                cursor.execute("""
                    SELECT pubname FROM pg_publication 
                    WHERE pubname = %s;
                """, (pub_name,))
                if not cursor.fetchone():
                    tables_str = ', '.join([f'"{t}"' for t in self.tables])
                    cursor.execute(f"""
                        CREATE PUBLICATION {pub_name} 
                        FOR TABLE {tables_str};
                    """)
                    logger.info(f"创建 publication: {pub_name}")
                
                logger.info("Logical replication 设置完成")
                return True
                
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            logger.error(f"设置 logical replication 失败: {e}")
            logger.info("需要数据库管理员权限才能设置 logical replication")
            return False

