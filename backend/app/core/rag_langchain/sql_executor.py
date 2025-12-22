"""
SQL执行服务
复用interface_executor的逻辑，提供SQL执行、结果处理、性能优化、安全控制
"""
import time
import re
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from loguru import logger

from app.models import DatabaseConfig
from app.core.db_factory import DatabaseConnectionFactory
from app.core.sql_dialect import SQLDialectFactory
from app.core.data_masking import DataMaskingService
from app.core.log_sanitizer import safe_log_sql
from app.core.cache import get_cache_service
from app.core.performance_monitor import get_performance_monitor, track_time


class SQLExecutor:
    """SQL执行服务"""
    
    def __init__(
        self,
        db_config: DatabaseConfig,
        timeout: int = 30,
        max_rows: int = 1000,
        enable_cache: bool = True,
        cache_ttl: int = 600  # 默认10分钟
    ):
        """
        初始化SQL执行器
        
        Args:
            db_config: 数据库配置
            timeout: 查询超时时间（秒）
            max_rows: 最大返回行数
            enable_cache: 是否启用缓存
            cache_ttl: 缓存过期时间（秒），默认10分钟
        """
        self.db_config = db_config
        self.timeout = timeout
        self.max_rows = max_rows
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.db_type = db_config.db_type or "mysql"
        self.cache_service = get_cache_service() if enable_cache else None
    
    def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行SQL查询
        
        Args:
            sql: SQL语句
            params: 参数化查询参数（可选）
            user_id: 用户ID（可选，用于审计）
            client_ip: 客户端IP（可选，用于审计）
            
        Returns:
            执行结果字典，包含：
            - success: 是否成功
            - data: 查询结果数据（列表）
            - row_count: 返回行数
            - total_rows: 实际查询到的行数
            - columns: 列名列表
            - execution_time: 执行时间（秒）
            - error: 错误信息（如果失败）
        """
        """
        执行SQL查询
        
        Args:
            sql: SQL语句
            params: 参数化查询参数
            user_id: 用户ID（用于审计）
            client_ip: 客户端IP（用于审计）
            
        Returns:
            执行结果字典
        """
        with track_time(f"SQL执行: {safe_log_sql(sql, 50)}"):
            return self._execute_sql_internal(sql, params, user_id, client_ip)
    
    def _execute_sql_internal(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """内部SQL执行方法"""
        start_time = time.time()
        
        # 0. 检查缓存（如果启用）
        if self.enable_cache and self.cache_service:
            cache_key = self._generate_cache_key(sql, params)
            cached_result = self.cache_service.get(cache_key)
            if cached_result:
                logger.info(f"从缓存获取SQL执行结果: {safe_log_sql(sql, 100)}")
                get_performance_monitor().record_sql_execution(0.001, from_cache=True)
                # 更新执行时间为当前时间（但保持原始执行时间信息）
                cached_result["execution_time"] = 0.001  # 缓存命中，几乎无耗时
                cached_result["from_cache"] = True
                return cached_result
        
        # 1. 安全验证
        self._validate_sql_safety(sql)
        
        # 2. 权限验证
        # 注意：查询权限验证功能待实现
        # 计划：基于用户角色和数据库配置的权限表进行验证
        # 当前：所有通过安全验证的查询都允许执行
        
        # 3. 执行SQL
        engine = None
        db = None
        try:
            engine = DatabaseConnectionFactory.create_engine(self.db_config)
            adapter = SQLDialectFactory.get_adapter(self.db_type)
            
            # 设置超时（在会话级别设置，而不是连接级别）
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            # 在会话级别设置MySQL超时
            if self.db_type == "mysql":
                try:
                    db.execute(text(f"SET SESSION max_execution_time = {self.timeout * 1000}"))
                except Exception as timeout_error:
                    logger.warning(f"设置MySQL超时失败: {timeout_error}")
            
            try:
                # 参数化查询（防止SQL注入）
                # 注意：即使params为空，也要检查SQL中是否有未绑定的参数占位符
                formatted_sql, query_params, unbound_params = self._parameterize_sql(sql, params or {}, adapter)
                
                # 执行查询 - 使用SQLAlchemy的参数绑定机制
                if query_params:
                    result = db.execute(text(formatted_sql), query_params)
                else:
                    result = db.execute(text(formatted_sql))
                rows = result.fetchall()
                columns = result.keys()
                
                # 4. 处理结果
                processed_data = self._process_results(rows, columns)
                
                elapsed_time = time.time() - start_time
                
                # 5. 审计日志
                self._log_query(sql, user_id, client_ip, elapsed_time, len(processed_data))
                
                # 6. 记录性能指标
                get_performance_monitor().record_sql_execution(elapsed_time, from_cache=False)
                
                result = {
                    "success": True,
                    "data": processed_data,
                    "row_count": len(processed_data),
                    "total_rows": len(rows),  # 实际查询到的行数（可能超过max_rows）
                    "columns": list(columns),
                    "execution_time": elapsed_time,
                    "from_cache": False,
                    "unbound_params": list(unbound_params) if unbound_params else []  # 传递未绑定参数信息
                }
                
                # 7. 缓存结果（如果启用且执行成功）
                if self.enable_cache and self.cache_service:
                    cache_key = self._generate_cache_key(sql, params)
                    # 只缓存较小的结果（避免内存占用过大）
                    if len(processed_data) <= 1000:
                        self.cache_service.set(cache_key, result, ttl=self.cache_ttl)
                        logger.debug(f"已缓存SQL执行结果: {safe_log_sql(sql, 100)}")
                
                return result
                
            finally:
                # 关闭数据库会话
                if db is not None:
                    try:
                        db.close()
                    except Exception as close_error:
                        logger.warning(f"关闭数据库会话时出错: {close_error}")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            
            # 审计日志（错误）
            self._log_query(sql, user_id, client_ip, elapsed_time, 0, error=error_msg)
            
            logger.error(f"SQL执行失败: {error_msg}", exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "data": [],
                "row_count": 0,
                "execution_time": elapsed_time,
                "from_cache": False
            }
        finally:
            # 注意：这里不dispose引擎，因为引擎应该被缓存和复用
            # 引擎的清理应该由引擎缓存机制管理（见问题#9）
            # 如果确实需要dispose，应该在引擎缓存中实现
            pass
    
    def _validate_sql_safety(self, sql: str):
        """
        验证SQL安全性
        
        Args:
            sql: SQL语句
            
        Raises:
            ValueError: 如果SQL不安全
        """
        sql_upper = sql.upper().strip()
        
        # 只允许SELECT语句或WITH子句（CTE）开头的SELECT语句
        # WITH子句格式：WITH ... AS (...) SELECT ...
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            raise ValueError("只允许执行SELECT查询语句")
        
        # 如果以WITH开头，必须包含SELECT
        if sql_upper.startswith("WITH") and "SELECT" not in sql_upper:
            raise ValueError("WITH子句必须包含SELECT语句")
        
        # 禁止危险操作（修改数据操作）
        # 使用正则表达式匹配单词边界，避免误判字段名（如created_at）
        import re
        dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE",
            "INSERT", "UPDATE", "REPLACE", "GRANT", "REVOKE",
            "EXEC", "EXECUTE", "CALL", "PROCEDURE", "FUNCTION"
        ]
        
        for keyword in dangerous_keywords:
            # 使用\b匹配单词边界，确保只匹配SQL关键字，不匹配字段名或字符串值
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_upper):
                raise ValueError(f"禁止执行包含 {keyword} 的SQL语句。您没有权限执行修改数据的操作，请使用查询操作。")
        
        # 检查是否查询所有数据明细（没有WHERE条件且没有LIMIT）
        import re
        # 检查是否有WHERE子句
        has_where = bool(re.search(r'\bWHERE\b', sql_upper))
        # 检查是否有LIMIT子句
        has_limit = bool(re.search(r'\bLIMIT\s+\d+\b', sql_upper))
        # 检查是否有聚合函数（COUNT, SUM等），如果有聚合函数，通常不是查询所有明细
        has_aggregate = bool(re.search(r'\b(COUNT|SUM|AVG|MAX|MIN|GROUP\s+BY)\b', sql_upper))
        
        # 如果没有WHERE、没有LIMIT、没有聚合函数，可能是查询所有数据明细
        if not has_where and not has_limit and not has_aggregate:
            # 检查SELECT的字段，如果是SELECT *，则很可能是查询所有明细
            if re.search(r'SELECT\s+\*', sql_upper):
                raise ValueError("为了数据安全和性能考虑，不允许查询所有数据明细。请添加WHERE条件、LIMIT限制或使用聚合函数（如COUNT、SUM等）进行统计查询。")
        
        # 检查SQL注入模式（更精确的检测，减少误报）
        # 注意：这些模式需要更精确，避免误判合法的SQL语句
        sql_injection_patterns = [
            # 检测SQL注释注入（'; -- 或 '; #）
            r"';\s*--",  # 单引号后跟分号和注释
            r"';\s*#",   # 单引号后跟分号和#注释
            # 检测UNION注入（必须是UNION后直接跟SELECT，且不在合法上下文中）
            r"\bUNION\s+ALL\s+SELECT\s+.*FROM\s+information_schema",  # 信息泄露
            r"\bUNION\s+SELECT\s+.*FROM\s+sys\.",  # 系统表访问
            # 检测危险函数调用
            r"\bxp_cmdshell\s*\(",  # SQL Server命令执行
            r"\bLOAD_FILE\s*\(",     # MySQL文件读取
            r"\bINTO\s+OUTFILE",    # MySQL文件写入（但需要更精确，避免误判SELECT INTO）
        ]
        
        for pattern in sql_injection_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                # 记录详细的SQL片段以便调试
                match = re.search(pattern, sql_upper, re.IGNORECASE)
                logger.warning(f"检测到潜在的SQL注入模式: {pattern}, SQL片段: {sql[match.start():match.end()+50] if match else 'N/A'}")
                raise ValueError("检测到潜在的SQL注入攻击")
    
    def _parameterize_sql(self, sql: str, params: Dict[str, Any], adapter) -> Tuple[str, Dict[str, Any], set]:
        """
        参数化SQL（防止SQL注入）
        
        Args:
            sql: SQL语句
            params: 参数字典
            adapter: SQL方言适配器
            
        Returns:
            (SQL语句, 参数字典, 未绑定参数集合) 元组，用于SQLAlchemy的参数化查询
        """
        # 如果SQL已经包含参数占位符（:param_name），处理参数绑定
        if ':' in sql:
            # 检查SQL中的占位符
            placeholder_pattern = r':(\w+)'
            placeholders_in_sql = re.findall(placeholder_pattern, sql)
            
            # 只返回SQL中实际使用的参数（且params中提供了值）
            filtered_params = {k: v for k, v in params.items() if k in placeholders_in_sql}
            
            # 检查是否有未绑定的参数（SQL中有占位符但params中没有值）
            unbound_params = set(placeholders_in_sql) - set(filtered_params.keys())
            
            if unbound_params:
                # 移除未绑定的参数占位符，替换为合理的默认值或移除条件
                logger.warning(f"检测到未绑定的SQL参数: {unbound_params}，将自动处理")
                processed_sql = sql
                
                for param_name in unbound_params:
                    # 根据参数在SQL中的使用方式，决定如何处理
                    # 优先移除包含未绑定参数的条件
                    
                    # 模式1: WHERE column != :param_name 或 WHERE column = :param_name（包括在CTE中）
                    # 匹配模式：column != :param_name 或 column = :param_name（可能前面有AND/OR）
                    pattern_condition = rf'(?:\s+(?:AND|OR)\s+)?\w+\s*(?:!=|<>|=)\s*:{param_name}\b'
                    
                    # 先移除AND/OR连接的条件
                    processed_sql = re.sub(
                        rf'\s+(?:AND|OR)\s+\w+\s*(?:!=|<>|=)\s*:{param_name}\b',
                        '',
                        processed_sql,
                        flags=re.IGNORECASE
                    )
                    
                    # 处理WHERE子句中的第一个条件
                    processed_sql = re.sub(
                        rf'\bWHERE\s+\w+\s*(?:!=|<>|=)\s*:{param_name}\b',
                        'WHERE 1=1',
                        processed_sql,
                        flags=re.IGNORECASE
                    )
                    
                    # 处理HAVING子句中的条件
                    processed_sql = re.sub(
                        rf'\bHAVING\s+\w+\s*(?:!=|<>|=)\s*:{param_name}\b',
                        'HAVING 1=1',
                        processed_sql,
                        flags=re.IGNORECASE
                    )
                    
                    # 如果还有未处理的占位符，替换为NULL（保守处理）
                    if f':{param_name}' in processed_sql:
                        processed_sql = processed_sql.replace(f':{param_name}', 'NULL')
                    
                    # 清理可能的空WHERE/HAVING子句
                    processed_sql = re.sub(r'\s+WHERE\s+1\s*=\s*1(?:\s+(?:AND|OR))?\s*$', '', processed_sql, flags=re.IGNORECASE)
                    processed_sql = re.sub(r'\s+HAVING\s+1\s*=\s*1(?:\s+(?:AND|OR))?\s*$', '', processed_sql, flags=re.IGNORECASE)
                
                sql = processed_sql
                logger.info(f"已处理未绑定参数，修改后的SQL预览: {sql[:200]}...")
            
            return sql, filtered_params, unbound_params
        
        # 如果SQL中没有占位符，返回原始SQL和空参数字典
        return sql, {}, set()
    
    def _process_results(
        self,
        rows: List[Any],
        columns: Any
    ) -> List[Dict[str, Any]]:
        """
        处理查询结果（包含数据脱敏）
        
        Args:
            rows: 查询结果行
            columns: 列名
            
        Returns:
            处理后的数据列表（已脱敏）
        """
        data = []
        column_list = list(columns) if hasattr(columns, '__iter__') else list(columns)
        
        for row in rows[:self.max_rows]:  # 限制行数
            row_dict = {}
            for i, col in enumerate(column_list):
                value = row[i]
                
                # 数据类型转换
                if value is None:
                    row_dict[col] = None
                elif hasattr(value, 'isoformat'):
                    # 日期时间类型
                    row_dict[col] = value.isoformat()
                elif isinstance(value, (int, float)):
                    # 数值类型
                    row_dict[col] = value
                elif isinstance(value, bytes):
                    # 二进制类型
                    try:
                        row_dict[col] = value.decode('utf-8')
                    except:
                        row_dict[col] = str(value)
                else:
                    # 字符串类型
                    row_dict[col] = str(value)
            
            data.append(row_dict)
        
        # 对数据进行脱敏处理（隐私信息保护）
        try:
            data = DataMaskingService.mask_data(data, column_list)
            logger.debug(f"已对查询结果进行数据脱敏处理，共处理 {len(data)} 条记录")
        except Exception as e:
            logger.warning(f"数据脱敏处理失败: {e}，返回原始数据")
            # 脱敏失败不影响主流程，返回原始数据
        
        return data
    
    def _generate_cache_key(self, sql: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        生成SQL执行缓存键
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            缓存键字符串
        """
        # 构建缓存键数据
        key_data = {
            "sql": sql.strip().upper(),  # 规范化SQL（去除空格，转大写）
            "params": params or {},
            "db_config_id": self.db_config.id,
            "max_rows": self.max_rows
        }
        
        # 生成hash
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        return f"sql_execution:{key_hash}"
    
    def _log_query(
        self,
        sql: str,
        user_id: Optional[int],
        client_ip: Optional[str],
        execution_time: float,
        row_count: int,
        error: Optional[str] = None
    ):
        """
        记录查询审计日志
        
        Args:
            sql: SQL语句
            user_id: 用户ID
            client_ip: 客户端IP
            execution_time: 执行时间
            row_count: 返回行数
            error: 错误信息（如果有）
        """
        log_data = {
            "sql": safe_log_sql(sql, 200),  # 脱敏后记录前200字符
            "user_id": user_id,
            "client_ip": client_ip,
            "execution_time": execution_time,
            "row_count": row_count,
            "success": error is None,
            "error": error
        }
        
        if error:
            logger.warning(f"SQL查询审计: {log_data}")
        else:
            logger.info(f"SQL查询审计: {log_data}")
        
        # 注意：审计日志保存到数据库功能待实现
        # 计划：创建audit_logs表，记录所有SQL查询的审计信息
        # 当前：仅记录到日志文件
    
    def execute_with_pagination(
        self,
        sql: str,
        page: int = 1,
        page_size: int = 100,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分页执行SQL查询
        
        Args:
            sql: SQL语句
            page: 页码（从1开始）
            page_size: 每页大小
            params: 参数
            
        Returns:
            分页结果
        """
        try:
            adapter = SQLDialectFactory.get_adapter(self.db_type)
            
            # 构建分页SQL
            paginated_sql = adapter.add_pagination(sql, page, page_size)
            
            # 执行查询
            result = self.execute(paginated_sql, params)
            
            if result["success"]:
                # 计算总数（需要执行COUNT查询）
                count_sql = adapter.get_count_sql(sql)
                count_result = self.execute(count_sql, params)
                
                total = 0
                if count_result.get("success") and count_result.get("data"):
                    total = count_result["data"][0].get("count", 0) if count_result["data"] else 0
                
                return {
                    **result,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total,
                        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
                    }
                }
            
            return result
        except Exception as e:
            logger.error(f"分页查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }

