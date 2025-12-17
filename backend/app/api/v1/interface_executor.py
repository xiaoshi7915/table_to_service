"""
接口执行路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.core.database import get_local_db
from app.models import User, InterfaceConfig, DatabaseConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user, get_current_user
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import json
import time

router = APIRouter(prefix="/api/v1/interfaces", tags=["接口执行"])


def get_database_connection_url(db_config: DatabaseConfig) -> str:
    """根据数据库配置生成连接URL"""
    # 使用quote_plus正确编码密码中的特殊字符
    encoded_password = quote_plus(db_config.password) if db_config.password else ""
    encoded_username = quote_plus(db_config.username) if db_config.username else ""
    return f"mysql+pymysql://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.database}?charset={db_config.charset or 'utf8mb4'}"


def check_rate_limit(interface_config: InterfaceConfig, client_ip: str) -> bool:
    """检查限流（简单实现，实际应该使用Redis等）"""
    if not interface_config.enable_rate_limit:
        return True
    
    # TODO: 实际应该使用Redis实现限流
    # 这里简单返回True，表示通过限流检查
    logger.info("接口 {} 启用限流，客户端IP: {}", interface_config.id, client_ip)
    return True


def ip_in_range(ip: str, ip_range: str) -> bool:
    """检查IP是否在指定范围内（支持CIDR格式）"""
    import ipaddress
    try:
        if '/' in ip_range:
            # CIDR格式
            network = ipaddress.ip_network(ip_range, strict=False)
            return ipaddress.ip_address(ip) in network
        else:
            # 单个IP
            return ip == ip_range
    except:
        return False


def check_whitelist(interface_config: InterfaceConfig, client_ip: str) -> bool:
    """检查白名单"""
    if not interface_config.enable_whitelist:
        return True
    
    # 如果没有配置白名单IP，默认拒绝
    if not interface_config.whitelist_ips or not interface_config.whitelist_ips.strip():
        logger.warning("接口 {} 启用白名单但未配置IP地址，拒绝访问", interface_config.id)
        return False
    
    # 解析白名单IP列表（换行分隔）
    whitelist_ips = [ip.strip() for ip in interface_config.whitelist_ips.split('\n') if ip.strip()]
    
    # 检查客户端IP是否在白名单中
    for ip_range in whitelist_ips:
        if ip_in_range(client_ip, ip_range):
            logger.info("接口 {} 白名单检查通过，客户端IP: {} 匹配 {}", interface_config.id, client_ip, ip_range)
            return True
    
    logger.warning("接口 {} 白名单检查失败，客户端IP: {} 不在白名单中", interface_config.id, client_ip)
    return False


def check_blacklist(interface_config: InterfaceConfig, client_ip: str) -> bool:
    """检查黑名单"""
    if not interface_config.enable_blacklist:
        return True
    
    # 如果没有配置黑名单IP，默认通过
    if not interface_config.blacklist_ips or not interface_config.blacklist_ips.strip():
        return True
    
    # 解析黑名单IP列表（换行分隔）
    blacklist_ips = [ip.strip() for ip in interface_config.blacklist_ips.split('\n') if ip.strip()]
    
    # 检查客户端IP是否在黑名单中
    for ip_range in blacklist_ips:
        if ip_in_range(client_ip, ip_range):
            logger.warning("接口 {} 黑名单检查失败，客户端IP: {} 匹配黑名单 {}", interface_config.id, client_ip, ip_range)
            return False
    
    return True


def audit_log(interface_config: InterfaceConfig, client_ip: str, user_id: Optional[int], action: str, details: Dict[str, Any]):
    """记录审计日志"""
    if not interface_config.enable_audit_log:
        return
    
    logger.info(
        f"审计日志 - 接口ID: {interface_config.id}, "
        f"接口名称: {interface_config.interface_name}, "
        f"客户端IP: {client_ip}, "
        f"用户ID: {user_id}, "
        f"操作: {action}, "
        f"详情: {details}"
    )
    # TODO: 实际应该写入专门的审计日志表


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 优先从X-Forwarded-For获取（代理服务器）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # 其次从X-Real-IP获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 最后从request.client获取
    if request.client:
        return request.client.host
    
    return "unknown"


def execute_interface_sql(
    interface_config: InterfaceConfig,
    db_config: DatabaseConfig,
    params: Dict[str, Any],
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    client_ip: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    执行接口SQL
    """
    try:
        # 创建数据库连接
        db_url = get_database_connection_url(db_config)
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 获取SQL语句
            sql = None
            
            # 如果是图形模式，需要构建SQL
            if interface_config.entry_mode == "graphical":
                sql = build_sql_from_graphical_config(interface_config, params)
            else:
                # 专家模式：使用配置的SQL语句
                sql = interface_config.sql_statement
            
            if not sql:
                raise ValueError("SQL语句为空")
            
            # 专家模式：使用参数化查询（防止SQL注入）
            # 注意：这里使用text()和参数绑定，但需要确保SQL语句中的参数使用:param_name格式
            # 如果SQL中已经使用了:param_name格式，SQLAlchemy会自动处理参数绑定
            # 但为了兼容性，我们仍然需要处理字符串替换（已转义）
            if interface_config.entry_mode == "expert":
                # 转义单引号防止SQL注入
                def escape_sql_string(value):
                    """转义SQL字符串值，防止SQL注入"""
                    if isinstance(value, str):
                        # 转义单引号：' -> ''
                        escaped = value.replace("'", "''")
                        # 转义反斜杠：\ -> \\
                        escaped = escaped.replace("\\", "\\\\")
                        return escaped
                    return str(value)
                
                for key, value in params.items():
                    placeholder = f":{key}"
                    if placeholder in sql:
                        # 对于字符串值，转义后加引号
                        if isinstance(value, str):
                            escaped_value = escape_sql_string(value)
                            sql = sql.replace(placeholder, f"'{escaped_value}'")
                        else:
                            sql = sql.replace(placeholder, str(value))
            
            # 检查最大查询数量限制（仅在非分页模式下应用）
            if not interface_config.enable_pagination and interface_config.max_query_count:
                # 添加LIMIT限制
                if "LIMIT" not in sql.upper():
                    sql = f"{sql} LIMIT {interface_config.max_query_count}"
            
            # 记录审计日志（执行前）
            if client_ip:
                audit_log(interface_config, client_ip, user_id, "execute_sql", {
                    "sql_preview": sql[:200] if sql else None,
                    "params": params
                })
            
            # 执行查询
            result = db.execute(text(sql))
            rows = result.fetchall()
            
            # 转换为字典列表，处理特殊类型（datetime, decimal等）
            columns = result.keys()
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    # 处理datetime类型
                    if hasattr(val, 'isoformat'):
                        row_dict[col] = val.isoformat()
                    # 处理decimal类型
                    elif hasattr(val, '__float__'):
                        try:
                            row_dict[col] = float(val)
                        except (ValueError, TypeError):
                            row_dict[col] = str(val)
                    # 处理None
                    elif val is None:
                        row_dict[col] = None
                    # 其他类型直接使用
                    else:
                        row_dict[col] = val
                data.append(row_dict)
            
            # 处理分页
            total = len(data)
            if interface_config.enable_pagination and page and page_size:
                start = (page - 1) * page_size
                end = start + page_size
                data = data[start:end]
            
            # 如果需要返回总数，执行COUNT查询
            total_count = total
            if interface_config.return_total_count:
                # 构建COUNT查询（使用原始SQL，不包含LIMIT）
                count_sql = sql
                # 移除LIMIT子句（如果存在）
                import re
                count_sql = re.sub(r'\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?', '', count_sql, flags=re.IGNORECASE)
                count_sql = f"SELECT COUNT(*) as total FROM ({count_sql}) as subquery"
                count_result = db.execute(text(count_sql))
                total_count = count_result.scalar() or total
            
            # 构建返回结果
            result = {
                "data": data,
                "count": len(data)
            }
            
            # 如果启用分页或返回总数，添加分页信息
            if interface_config.enable_pagination:
                result["pageNumber"] = page or 1
                result["pageSize"] = page_size or len(data)
            
            if interface_config.return_total_count:
                result["total"] = total_count
            
            return result
        finally:
            db.close()
            engine.dispose()
    except Exception as e:
        logger.error("执行接口SQL失败: {}", e, exc_info=True)
        raise


def escape_identifier(identifier: str) -> str:
    """转义SQL标识符（字段名、表名），使用反引号包裹以避免与保留关键字冲突"""
    if not identifier:
        return identifier
    # 如果已经包含反引号，直接返回
    if identifier.startswith("`") and identifier.endswith("`"):
        return identifier
    return f"`{identifier}`"


def build_sql_from_graphical_config(interface_config: InterfaceConfig, params: Dict[str, Any]) -> str:
    """从图形配置构建SQL"""
    # 构建SELECT字段
    if interface_config.selected_fields:
        # 为每个字段名添加反引号
        fields = ", ".join([escape_identifier(field) for field in interface_config.selected_fields])
    else:
        fields = "*"
    
    # 构建FROM子句
    table_name = interface_config.table_name
    if not table_name:
        raise ValueError("表名不能为空")
    
    # 为表名添加反引号
    escaped_table_name = escape_identifier(table_name)
    sql = f"SELECT {fields} FROM {escaped_table_name}"
    
    # 构建WHERE子句
    where_conditions = interface_config.where_conditions or []
    if where_conditions:
        where_parts = []
        for cond in where_conditions:
            field = cond.get("field")
            operator = cond.get("operator", "equal")
            value_type = cond.get("value_type", "constant")
            value = cond.get("value")
            variable_name = cond.get("variable_name")
            logic = cond.get("logic", "AND")
            
            if not field:
                continue
            
            # 转义字段名
            escaped_field = escape_identifier(field)
            
            # 构建条件表达式
            if operator == "equal":
                op = "="
            elif operator == "not_equal":
                op = "!="
            elif operator == "greater":
                op = ">"
            elif operator == "greater_equal":
                op = ">="
            elif operator == "less":
                op = "<"
            elif operator == "less_equal":
                op = "<="
            elif operator == "like":
                op = "LIKE"
            elif operator == "not_like":
                op = "NOT LIKE"
            elif operator == "in":
                op = "IN"
            elif operator == "not_in":
                op = "NOT IN"
            elif operator == "is_null":
                where_parts.append(f"{escaped_field} IS NULL")
                continue
            elif operator == "is_not_null":
                where_parts.append(f"{escaped_field} IS NOT NULL")
                continue
            else:
                op = "="
            
            # 转义SQL字符串值，防止SQL注入
            def escape_sql_value(val):
                """转义SQL字符串值"""
                if isinstance(val, str):
                    # 转义单引号：' -> ''
                    escaped = val.replace("'", "''")
                    # 转义反斜杠：\ -> \\
                    escaped = escaped.replace("\\", "\\\\")
                    return escaped
                return str(val)
            
            # 获取值
            if value_type == "variable" and variable_name:
                # 从参数中获取值
                param_value = params.get(variable_name)
                if param_value is None:
                    continue
                if operator in ["like", "not_like"]:
                    escaped_val = escape_sql_value(param_value)
                    cond_value = f"'{escaped_val}'"
                elif operator in ["in", "not_in"]:
                    if isinstance(param_value, list):
                        values = ", ".join([f"'{escape_sql_value(v)}'" if isinstance(v, str) else str(v) for v in param_value])
                    else:
                        escaped_val = escape_sql_value(param_value)
                        values = f"'{escaped_val}'"
                    cond_value = f"({values})"
                else:
                    if isinstance(param_value, str):
                        escaped_val = escape_sql_value(param_value)
                        cond_value = f"'{escaped_val}'"
                    else:
                        cond_value = str(param_value)
            else:
                # 常量值
                if operator in ["like", "not_like"]:
                    escaped_val = escape_sql_value(value)
                    cond_value = f"'{escaped_val}'"
                elif operator in ["in", "not_in"]:
                    if isinstance(value, list):
                        values = ", ".join([f"'{escape_sql_value(v)}'" if isinstance(v, str) else str(v) for v in value])
                    else:
                        escaped_val = escape_sql_value(value)
                        values = f"'{escaped_val}'"
                    cond_value = f"({values})"
                else:
                    if isinstance(value, str):
                        escaped_val = escape_sql_value(value)
                        cond_value = f"'{escaped_val}'"
                    else:
                        cond_value = str(value)
            
            where_parts.append(f"{escaped_field} {op} {cond_value}")
        
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
    
    # 构建ORDER BY子句
    order_by_fields = interface_config.order_by_fields or []
    if order_by_fields:
        order_parts = []
        for order in order_by_fields:
            field = order.get("field")
            direction = order.get("direction", "ASC")
            if field:
                # 转义字段名
                escaped_field = escape_identifier(field)
                order_parts.append(f"{escaped_field} {direction}")
        if order_parts:
            sql += " ORDER BY " + ", ".join(order_parts)
    
    return sql


@router.get("/{config_id}/execute", response_model=ResponseModel)
async def execute_interface_get(
    config_id: int,
    request: Request,
    pageNumber: Optional[int] = Query(None, ge=1, alias="pageNumber"),
    pageSize: Optional[int] = Query(None, ge=1, le=1000, alias="pageSize"),
    # 兼容旧参数名
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """执行接口（GET请求）"""
    try:
        # 获取接口配置
        interface_config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not interface_config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 允许执行草稿状态的接口（用于测试），但禁用状态的接口不能执行
        if interface_config.status == "inactive":
            raise HTTPException(status_code=400, detail="接口已禁用，无法执行。请将接口状态设置为'激活'或'草稿'")
        
        # 检查图形模式下的必要字段
        if interface_config.entry_mode == "graphical":
            if not interface_config.table_name:
                raise HTTPException(
                    status_code=400, 
                    detail="图形模式接口配置不完整：表名为空。请编辑接口配置，在图形模式下选择数据表。"
                )
        
        # 获取数据库配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == interface_config.database_config_id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 检查认证
        if interface_config.proxy_auth != "no_auth":
            # 需要认证，验证token
            try:
                current_user = await get_current_user(request, db)
            except:
                raise HTTPException(status_code=401, detail="需要认证")
        
        # 获取查询参数
        params = dict(request.query_params)
        
        # 处理分页参数：优先使用 pageNumber/pageSize，兼容 page/page_size
        actual_page = pageNumber if pageNumber is not None else page
        actual_page_size = pageSize if pageSize is not None else page_size
        
        # 如果启用分页，使用分页参数；否则使用最大查询数量限制
        if interface_config.enable_pagination:
            # 分页模式：使用 pageNumber 和 pageSize
            if actual_page is None:
                actual_page = 1
            if actual_page_size is None:
                actual_page_size = 10
            # 移除分页参数，避免传递给SQL
            params.pop("pageNumber", None)
            params.pop("pageSize", None)
            params.pop("page", None)
            params.pop("page_size", None)
        else:
            # 非分页模式：使用 max_query_count 限制
            actual_page = None
            actual_page_size = None
            # 移除分页参数
            params.pop("pageNumber", None)
            params.pop("pageSize", None)
            params.pop("page", None)
            params.pop("page_size", None)
        
        # 执行SQL
        result = execute_interface_sql(
            interface_config,
            db_config,
            params,
            actual_page,
            actual_page_size
        )
        
        # 构建响应
        response_data = ResponseModel(
            success=True,
            message="执行成功",
            data=result
        )
        
        # 构建响应头
        headers = {}
        
        # 如果启用了跨域，添加CORS响应头
        if interface_config.enable_cors:
            if interface_config.cors_allow_origin:
                headers["Access-Control-Allow-Origin"] = interface_config.cors_allow_origin
            if interface_config.cors_expose_headers:
                headers["Access-Control-Expose-Headers"] = interface_config.cors_expose_headers
            if interface_config.cors_max_age:
                headers["Access-Control-Max-Age"] = str(interface_config.cors_max_age)
            if interface_config.cors_allow_methods:
                headers["Access-Control-Allow-Methods"] = interface_config.cors_allow_methods
            if interface_config.cors_allow_headers:
                headers["Access-Control-Allow-Headers"] = interface_config.cors_allow_headers
            if interface_config.cors_allow_credentials is not None:
                headers["Access-Control-Allow-Credentials"] = "true" if interface_config.cors_allow_credentials else "false"
        
        # 添加自定义HTTP响应头
        try:
            from app.models import InterfaceHeader
            response_headers = db.query(InterfaceHeader).filter(
                InterfaceHeader.interface_config_id == interface_config.id,
                InterfaceHeader.name.like("Response-%")
            ).all()
            for header in response_headers:
                # 移除Response-前缀
                header_name = header.name.replace("Response-", "", 1) if header.name.startswith("Response-") else header.name
                headers[header_name] = header.value
        except Exception as e:
            logger.warning("获取响应头失败: {}", e)
        
        # 如果有响应头，返回JSONResponse，否则返回普通ResponseModel
        if headers:
            return JSONResponse(
                content=response_data.dict(),
                headers=headers
            )
        
        return response_data
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error("执行接口失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行接口失败: {str(e)}"
        )


@router.post("/{config_id}/execute", response_model=ResponseModel)
async def execute_interface_post(
    config_id: int,
    request: Request,
    body: Dict[str, Any] = Body(None),
    pageNumber: Optional[int] = Query(None, ge=1, alias="pageNumber"),
    pageSize: Optional[int] = Query(None, ge=1, le=1000, alias="pageSize"),
    # 兼容旧参数名
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """执行接口（POST请求）"""
    try:
        # 获取接口配置
        interface_config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not interface_config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 允许执行草稿状态的接口（用于测试），但禁用状态的接口不能执行
        if interface_config.status == "inactive":
            raise HTTPException(status_code=400, detail="接口已禁用，无法执行。请将接口状态设置为'激活'或'草稿'")
        
        # 检查图形模式下的必要字段
        if interface_config.entry_mode == "graphical":
            if not interface_config.table_name:
                raise HTTPException(
                    status_code=400, 
                    detail="图形模式接口配置不完整：表名为空。请编辑接口配置，在图形模式下选择数据表。"
                )
        
        # 获取客户端IP
        client_ip = get_client_ip(request)
        
        # 检查白名单
        if not check_whitelist(interface_config, client_ip):
            raise HTTPException(status_code=403, detail="您的IP不在白名单中")
        
        # 检查黑名单
        if not check_blacklist(interface_config, client_ip):
            raise HTTPException(status_code=403, detail="您的IP已被加入黑名单")
        
        # 检查限流
        if not check_rate_limit(interface_config, client_ip):
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        
        # 获取数据库配置
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == interface_config.database_config_id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 检查认证
        if interface_config.proxy_auth != "no_auth":
            # 需要认证，验证token
            try:
                current_user = await get_current_user(request, db)
            except:
                raise HTTPException(status_code=401, detail="需要认证")
        
        # 获取参数（从请求体和query params）
        params = body or {}
        # 合并query参数
        query_params = dict(request.query_params)
        params.update(query_params)
        
        # 处理分页参数：优先使用 pageNumber/pageSize，兼容 page/page_size
        actual_page = pageNumber if pageNumber is not None else page
        actual_page_size = pageSize if pageSize is not None else page_size
        
        # 如果启用分页，使用分页参数；否则使用最大查询数量限制
        if interface_config.enable_pagination:
            # 分页模式：使用 pageNumber 和 pageSize
            if actual_page is None:
                actual_page = 1
            if actual_page_size is None:
                actual_page_size = 10
            # 移除分页参数，避免传递给SQL
            params.pop("pageNumber", None)
            params.pop("pageSize", None)
            params.pop("page", None)
            params.pop("page_size", None)
        else:
            # 非分页模式：使用 max_query_count 限制
            actual_page = None
            actual_page_size = None
            # 移除分页参数
            params.pop("pageNumber", None)
            params.pop("pageSize", None)
            params.pop("page", None)
            params.pop("page_size", None)
        
        # 执行SQL（带超时控制）
        import threading
        
        result = None
        error_occurred = threading.Event()
        
        def execute_with_timeout():
            nonlocal result
            try:
                result = execute_interface_sql(
                    interface_config,
                    db_config,
                    params,
                    actual_page,
                    actual_page_size,
                    client_ip,
                    current_user.id if current_user else None
                )
            except Exception as e:
                error_occurred.set()
                raise e
        
        # 如果启用了超时设置
        if interface_config.timeout_seconds and interface_config.timeout_seconds > 0:
            thread = threading.Thread(target=execute_with_timeout)
            thread.daemon = True
            thread.start()
            thread.join(timeout=interface_config.timeout_seconds)
            
            if thread.is_alive():
                raise HTTPException(status_code=504, detail=f"请求超时（超过{interface_config.timeout_seconds}秒）")
            
            if error_occurred.is_set():
                raise HTTPException(status_code=500, detail="执行失败")
        else:
            result = execute_interface_sql(
                interface_config,
                db_config,
                params,
                actual_page,
                actual_page_size,
                client_ip,
                current_user.id if current_user else None
            )
        
        # 构建响应
        response_data = ResponseModel(
            success=True,
            message="执行成功",
            data=result
        )
        
        # 构建响应头
        headers = {}
        
        # 如果启用了跨域，添加CORS响应头
        if interface_config.enable_cors:
            if interface_config.cors_allow_origin:
                headers["Access-Control-Allow-Origin"] = interface_config.cors_allow_origin
            if interface_config.cors_expose_headers:
                headers["Access-Control-Expose-Headers"] = interface_config.cors_expose_headers
            if interface_config.cors_max_age:
                headers["Access-Control-Max-Age"] = str(interface_config.cors_max_age)
            if interface_config.cors_allow_methods:
                headers["Access-Control-Allow-Methods"] = interface_config.cors_allow_methods
            if interface_config.cors_allow_headers:
                headers["Access-Control-Allow-Headers"] = interface_config.cors_allow_headers
            if interface_config.cors_allow_credentials is not None:
                headers["Access-Control-Allow-Credentials"] = "true" if interface_config.cors_allow_credentials else "false"
        
        # 添加自定义HTTP响应头
        try:
            from app.models import InterfaceHeader
            response_headers = db.query(InterfaceHeader).filter(
                InterfaceHeader.interface_config_id == interface_config.id,
                InterfaceHeader.name.like("Response-%")
            ).all()
            for header in response_headers:
                # 移除Response-前缀
                header_name = header.name.replace("Response-", "", 1) if header.name.startswith("Response-") else header.name
                headers[header_name] = header.value
        except Exception as e:
            logger.warning("获取响应头失败: {}", e)
        
        # 如果有响应头，返回JSONResponse，否则返回普通ResponseModel
        if headers:
            return JSONResponse(
                content=response_data.dict(),
                headers=headers
            )
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("执行接口失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行接口失败: {str(e)}"
        )

