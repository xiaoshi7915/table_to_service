"""
接口执行路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from database import get_local_db
from models import User, InterfaceConfig, DatabaseConfig
from schemas import ResponseModel
from auth import get_current_active_user, get_current_user
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
    logger.info(f"接口 {interface_config.id} 启用限流，客户端IP: {client_ip}")
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
        logger.warning(f"接口 {interface_config.id} 启用白名单但未配置IP地址，拒绝访问")
        return False
    
    # 解析白名单IP列表（换行分隔）
    whitelist_ips = [ip.strip() for ip in interface_config.whitelist_ips.split('\n') if ip.strip()]
    
    # 检查客户端IP是否在白名单中
    for ip_range in whitelist_ips:
        if ip_in_range(client_ip, ip_range):
            logger.info(f"接口 {interface_config.id} 白名单检查通过，客户端IP: {client_ip} 匹配 {ip_range}")
            return True
    
    logger.warning(f"接口 {interface_config.id} 白名单检查失败，客户端IP: {client_ip} 不在白名单中")
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
            logger.warning(f"接口 {interface_config.id} 黑名单检查失败，客户端IP: {client_ip} 匹配黑名单 {ip_range}")
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
    # #region agent log
    try:
        with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"H","location":"interface_executor.py:execute_interface_sql:entry","message":"执行SQL函数入口","data":{"entry_mode":interface_config.entry_mode,"has_sql":bool(interface_config.sql_statement),"enable_pagination":interface_config.enable_pagination},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        # 创建数据库连接
        db_url = get_database_connection_url(db_config)
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"H","location":"interface_executor.py:execute_interface_sql:before_engine","message":"创建数据库连接前","data":{"db_url_masked":db_url.split("@")[0].split(":")[0]+":***@"+db_url.split("@")[1] if "@" in db_url else db_url},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # 获取SQL语句
            sql = None
            
            # 如果是图形模式，需要构建SQL
            if interface_config.entry_mode == "graphical":
                # #region agent log
                try:
                    with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"I","location":"interface_executor.py:execute_interface_sql:graphical_mode","message":"图形模式，构建SQL","data":{"table_name":interface_config.table_name,"selected_fields":interface_config.selected_fields},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                sql = build_sql_from_graphical_config(interface_config, params)
            else:
                # 专家模式：使用配置的SQL语句
                sql = interface_config.sql_statement
            
            # #region agent log
            try:
                with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"I","location":"interface_executor.py:execute_interface_sql:sql_check","message":"SQL语句检查","data":{"has_sql":bool(sql),"sql_length":len(sql) if sql else 0,"entry_mode":interface_config.entry_mode},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            if not sql:
                raise ValueError("SQL语句为空")
            
            # 专家模式：替换参数（图形模式的参数已在build_sql_from_graphical_config中处理）
            if interface_config.entry_mode == "expert":
                for key, value in params.items():
                    placeholder = f":{key}"
                    if placeholder in sql:
                        # 对于字符串值，需要加引号
                        if isinstance(value, str):
                            sql = sql.replace(placeholder, f"'{value}'")
                        else:
                            sql = sql.replace(placeholder, str(value))
            
            # 检查最大查询数量限制
            if interface_config.max_query_count:
                # 添加LIMIT限制
                if "LIMIT" not in sql.upper():
                    sql = f"{sql} LIMIT {interface_config.max_query_count}"
            
            # 记录审计日志（执行前）
            if client_ip:
                audit_log(interface_config, client_ip, user_id, "execute_sql", {
                    "sql_preview": sql[:200] if sql else None,
                    "params": params
                })
            
            # #region agent log
            try:
                with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"J","location":"interface_executor.py:execute_interface_sql:before_execute","message":"执行SQL前","data":{"sql_preview":sql[:200] if sql else None},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            # 执行查询
            result = db.execute(text(sql))
            rows = result.fetchall()
            
            # #region agent log
            try:
                with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"J","location":"interface_executor.py:execute_interface_sql:after_execute","message":"执行SQL后","data":{"row_count":len(rows)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
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
                count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
                count_result = db.execute(text(count_sql))
                total_count = count_result.scalar() or total
            
            return {
                "data": data,
                "count": len(data),
                "total": total_count,
                "page": page or 1,
                "page_size": page_size or len(data)
            }
        finally:
            db.close()
            engine.dispose()
    except Exception as e:
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"K","location":"interface_executor.py:execute_interface_sql:exception","message":"执行SQL异常","data":{"error_type":type(e).__name__,"error_message":str(e)},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        logger.error(f"执行接口SQL失败: {e}", exc_info=True)
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
    
    # #region agent log
    try:
        with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"execute-sql","hypothesisId":"L","location":"interface_executor.py:build_sql_from_graphical_config:after_build","message":"构建SQL后","data":{"sql_preview":sql[:200] if sql else None},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    
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
            
            # 获取值
            if value_type == "variable" and variable_name:
                # 从参数中获取值
                param_value = params.get(variable_name)
                if param_value is None:
                    continue
                if operator in ["like", "not_like"]:
                    cond_value = f"'{param_value}'"
                elif operator in ["in", "not_in"]:
                    if isinstance(param_value, list):
                        values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in param_value])
                    else:
                        values = f"'{param_value}'"
                    cond_value = f"({values})"
                else:
                    cond_value = f"'{param_value}'" if isinstance(param_value, str) else str(param_value)
            else:
                # 常量值
                if operator in ["like", "not_like"]:
                    cond_value = f"'{value}'"
                elif operator in ["in", "not_in"]:
                    if isinstance(value, list):
                        values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                    else:
                        values = f"'{value}'"
                    cond_value = f"({values})"
                else:
                    cond_value = f"'{value}'" if isinstance(value, str) else str(value)
            
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
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """执行接口（GET请求）"""
    # #region agent log
    try:
        with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"A","location":"interface_executor.py:execute_interface_get:entry","message":"函数入口","data":{"config_id":config_id,"user_id":current_user.id,"page":page,"page_size":page_size},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        # 获取接口配置
        interface_config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"B","location":"interface_executor.py:execute_interface_get:after_query","message":"查询接口配置后","data":{"config_exists":interface_config is not None,"status":interface_config.status if interface_config else None,"entry_mode":interface_config.entry_mode if interface_config else None,"table_name":interface_config.table_name if interface_config else None,"database_config_id":interface_config.database_config_id if interface_config else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        
        if not interface_config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 允许执行草稿状态的接口（用于测试），但禁用状态的接口不能执行
        if interface_config.status == "inactive":
            # #region agent log
            try:
                with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"C","location":"interface_executor.py:execute_interface_get:status_check","message":"接口状态检查失败","data":{"status":interface_config.status},"timestamp":int(__import__("time").time()*1000)})+"\n")
            except: pass
            # #endregion
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
        
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"D","location":"interface_executor.py:execute_interface_get:after_db_query","message":"查询数据库配置后","data":{"db_config_exists":db_config is not None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        
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
        # 移除分页参数
        params.pop("page", None)
        params.pop("page_size", None)
        
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"E","location":"interface_executor.py:execute_interface_get:before_execute","message":"执行SQL前","data":{"params":params,"enable_pagination":interface_config.enable_pagination,"entry_mode":interface_config.entry_mode},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # 执行SQL
        result = execute_interface_sql(
            interface_config,
            db_config,
            params,
            page if interface_config.enable_pagination else None,
            page_size if interface_config.enable_pagination else None
        )
        
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"E","location":"interface_executor.py:execute_interface_get:after_execute","message":"执行SQL后","data":{"result_keys":list(result.keys()) if isinstance(result, dict) else "not_dict","has_data":bool(result.get("data")) if isinstance(result, dict) else False},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        
        return ResponseModel(
            success=True,
            message="执行成功",
            data=result
        )
    except HTTPException as e:
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"F","location":"interface_executor.py:execute_interface_get:http_exception","message":"HTTP异常","data":{"status_code":e.status_code,"detail":e.detail},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        raise
    except Exception as e:
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface","hypothesisId":"G","location":"interface_executor.py:execute_interface_get:exception","message":"执行异常","data":{"error_type":type(e).__name__,"error_message":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        logger.error(f"执行接口失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行接口失败: {str(e)}"
        )


@router.post("/{config_id}/execute", response_model=ResponseModel)
async def execute_interface_post(
    config_id: int,
    request: Request,
    body: Dict[str, Any] = Body(None),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
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
        
        # #region agent log
        try:
            with open(r"e:\工作\Coding\local_service\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"execute-interface-post","hypothesisId":"A","location":"interface_executor.py:execute_interface_post:after_query","message":"查询接口配置后","data":{"config_exists":interface_config is not None,"status":interface_config.status if interface_config else None,"entry_mode":interface_config.entry_mode if interface_config else None,"table_name":interface_config.table_name if interface_config else None,"database_config_id":interface_config.database_config_id if interface_config else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except: pass
        # #endregion
        
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
        
        # 获取参数（从请求体）
        params = body or {}
        # 移除分页参数
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
                    page if interface_config.enable_pagination else None,
                    page_size if interface_config.enable_pagination else None,
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
                page if interface_config.enable_pagination else None,
                page_size if interface_config.enable_pagination else None,
                client_ip,
                current_user.id if current_user else None
            )
        
        return ResponseModel(
            success=True,
            message="执行成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行接口失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行接口失败: {str(e)}"
        )

