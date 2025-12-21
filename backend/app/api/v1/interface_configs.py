"""
接口配置路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.core.database import get_local_db
from app.models import User, InterfaceConfig, InterfaceParameter, InterfaceHeader, DatabaseConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from loguru import logger
import sqlparse
from sqlparse.sql import Statement, IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
import json

router = APIRouter(prefix="/api/v1/interface-configs", tags=["接口配置"])


def parse_sql_parameters(sql: str) -> Dict[str, Any]:
    """
    解析SQL语句中的参数
    返回请求参数和响应参数
    """
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return {"request_parameters": [], "response_parameters": []}
        
        request_params = []
        response_params = []
        
        # 简单的参数提取：查找 :param_name 格式的参数
        import re
        param_pattern = r':(\w+)'
        params = re.findall(param_pattern, sql)
        
        # 去重并创建参数列表
        unique_params = list(set(params))
        for param_name in unique_params:
            request_params.append({
                "name": param_name,
                "type": "string",
                "description": f"参数 {param_name}",
                "constraint": "optional",
                "location": "query"
            })
        
        # 尝试从SELECT语句中提取响应字段
        for stmt in parsed:
            if stmt.get_type() == 'SELECT':
                # 查找SELECT后的字段列表
                tokens = stmt.tokens
                in_select = False
                select_fields_found = False
                for token in tokens:
                    if token.ttype is DML and token.value.upper() == 'SELECT':
                        in_select = True
                        continue
                    if in_select:
                        # 检查是否是SELECT *
                        if isinstance(token, sqlparse.sql.Token) and token.value.strip() == '*':
                            # SELECT * 的情况，无法从SQL中提取字段，返回空列表
                            # 字段信息需要从实际执行结果或表结构中获取
                            break
                        elif isinstance(token, IdentifierList):
                            # SELECT field1, field2, ... 的情况
                            for identifier in token.get_identifiers():
                                if isinstance(identifier, Identifier):
                                    field_name = identifier.get_real_name()
                                    response_params.append({
                                        "name": field_name,
                                        "type": "string",
                                        "description": f"字段 {field_name}",
                                        "constraint": "required"
                                    })
                            select_fields_found = True
                            break
                        elif isinstance(token, Identifier):
                            # SELECT field 的情况（单个字段）
                            field_name = token.get_real_name()
                            response_params.append({
                                "name": field_name,
                                "type": "string",
                                "description": f"字段 {field_name}",
                                "constraint": "required"
                            })
                            select_fields_found = True
                            break
        
        return {
            "request_parameters": request_params,
            "response_parameters": response_params
        }
    except Exception as e:
        logger.error("解析SQL参数失败: {}", e, exc_info=True)
        return {"request_parameters": [], "response_parameters": []}


@router.post("/parse-sql", response_model=ResponseModel)
async def parse_sql(
    sql_data: Dict[str, str],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """解析SQL语句，提取参数"""
    try:
        sql = sql_data.get("sql", "")
        if not sql:
            raise HTTPException(status_code=400, detail="SQL语句不能为空")
        
        result = parse_sql_parameters(sql)
        return ResponseModel(
            success=True,
            message="解析成功",
            data=result
        )
    except Exception as e:
        logger.error("解析SQL失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析SQL失败: {str(e)}"
        )


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_configs(
    database_id: Optional[int] = Query(None, description="数据库ID"),
    status: Optional[str] = Query(None, description="状态过滤"),
    entry_mode: Optional[str] = Query(None, description="录入模式过滤"),
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(10, ge=1, le=1000, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取接口配置列表（支持分页）"""
    try:
        query = db.query(InterfaceConfig).filter(
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        )
        
        if database_id:
            query = query.filter(InterfaceConfig.database_config_id == database_id)
        
        if status:
            query = query.filter(InterfaceConfig.status == status)
        
        if entry_mode:
            query = query.filter(InterfaceConfig.entry_mode == entry_mode)
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        configs = query.order_by(InterfaceConfig.created_at.desc()).offset(offset).limit(page_size).all()
        
        result = []
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(
                DatabaseConfig.id == config.database_config_id,
                DatabaseConfig.is_deleted == False
            ).first()
            result.append({
                "id": config.id,
                "interface_name": config.interface_name,
                "database_name": db_config.name if db_config else "",
                "entry_mode": config.entry_mode,
                "status": config.status,
                "proxy_path": config.proxy_path,
                "http_method": config.http_method,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except Exception as e:
        logger.error("获取接口配置列表失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口配置列表失败: {str(e)}"
        )


@router.get("/{config_id}", response_model=ResponseModel)
async def get_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取接口配置详情"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
        
        # 获取请求参数和响应参数
        request_parameters = []
        response_parameters = []
        
        if config.entry_mode == "expert" and config.sql_statement:
            # 专家模式：从SQL中解析参数
            parsed = parse_sql_parameters(config.sql_statement)
            request_parameters = parsed.get("request_parameters", [])
            response_parameters = parsed.get("response_parameters", [])
            
            # 如果响应参数为空（例如SELECT *的情况），尝试从实际执行结果中获取
            if not response_parameters:
                try:
                    from app.api.v1.interface_executor import execute_interface_sql
                    # 执行一次查询获取字段信息（使用LIMIT 1避免大量数据）
                    test_result = execute_interface_sql(
                        config,
                        db_config,
                        {},  # 空参数
                        page=1,
                        page_size=1,
                        client_ip=None,
                        user_id=current_user.id
                    )
                    if test_result and isinstance(test_result, dict) and test_result.get("data"):
                        first_row = test_result.get("data", [])
                        if first_row and len(first_row) > 0 and isinstance(first_row[0], dict):
                            for field_name in first_row[0].keys():
                                # 推断字段类型
                                field_value = first_row[0][field_name]
                                field_type = "string"
                                if isinstance(field_value, int):
                                    field_type = "integer"
                                elif isinstance(field_value, float):
                                    field_type = "number"
                                elif isinstance(field_value, bool):
                                    field_type = "boolean"
                                
                                response_parameters.append({
                                    "name": field_name,
                                    "type": field_type,
                                    "description": f"字段 {field_name}",
                                    "constraint": "required"
                                })
                except Exception as e:
                    logger.warning(f"尝试从实际执行结果获取响应参数失败: {e}")
        elif config.entry_mode == "graphical":
            # 图形模式：从WHERE条件中提取请求参数
            if config.where_conditions:
                for cond in config.where_conditions:
                    if cond.get("value_type") == "variable" and cond.get("variable_name"):
                        request_parameters.append({
                            "name": cond.get("variable_name"),
                            "type": "string",
                            "description": cond.get("description", ""),
                            "constraint": "required" if cond.get("required", True) else "optional",
                            "location": "query"
                        })
            # 图形模式：从selected_fields中提取响应参数（数据字段）
            if config.selected_fields:
                for field in config.selected_fields:
                    response_parameters.append({
                        "name": field,
                        "type": "string",  # 默认类型，实际类型可以从数据库schema获取
                        "description": f"字段 {field}",
                        "constraint": "required"
                    })
        
        # 获取保存的请求参数（从数据库）
        saved_params = db.query(InterfaceParameter).filter(
            InterfaceParameter.interface_config_id == config_id,
            InterfaceParameter.is_deleted == False
        ).all()
        saved_request_parameters = []
        for param in saved_params:
            saved_request_parameters.append({
                "name": param.name,
                "type": param.type,
                "description": param.description,
                "constraint": param.constraint,
                "location": param.location,
                "default_value": param.default_value
            })
        
        # 如果数据库中没有保存的参数，使用解析的参数
        if not saved_request_parameters:
            saved_request_parameters = request_parameters
        
        # 如果启用了分页，添加分页参数到请求参数
        if config.enable_pagination:
            # 检查是否已经存在分页参数，避免重复添加
            has_page_number = any(p.get("name") == "pageNumber" for p in saved_request_parameters)
            has_page_size = any(p.get("name") == "pageSize" for p in saved_request_parameters)
            
            if not has_page_number:
                saved_request_parameters.append({
                    "name": "pageNumber",
                    "type": "integer",
                    "description": "页码，从1开始",
                    "constraint": "optional",
                    "location": "query"
                })
            if not has_page_size:
                saved_request_parameters.append({
                    "name": "pageSize",
                    "type": "integer",
                    "description": "每页数量，最大1000",
                    "constraint": "optional",
                    "location": "query"
                })
        
        
        # 获取保存的响应头（从数据库）
        saved_headers = db.query(InterfaceHeader).filter(
            InterfaceHeader.interface_config_id == config_id,
            InterfaceHeader.name.like("Response-%"),
            InterfaceHeader.is_deleted == False
        ).all()
        response_headers_list = []
        for header in saved_headers:
            # 移除Response-前缀
            header_name = header.name.replace("Response-", "", 1) if header.name.startswith("Response-") else header.name
            response_headers_list.append({
                "name": header_name,
                "value": header.value,
                "description": header.description or ""
            })
        
        # 构建返回数据
        result = {
            "id": config.id,
            "interface_name": config.interface_name,
            "interface_description": config.interface_description,
            "usage_instructions": config.usage_instructions,
            "category": config.category,
            "status": config.status,
            "entry_mode": config.entry_mode,
            "sql_statement": config.sql_statement,
            "table_name": config.table_name,
            "selected_fields": config.selected_fields,
            "where_conditions": config.where_conditions,
            "order_by_fields": config.order_by_fields,
            "database_config_id": config.database_config_id,
            "database_name": db_config.name if db_config else "",
            "sync_to_gateway": config.sync_to_gateway,
            "extension_fields": config.extension_fields,
            "http_method": config.http_method,
            "proxy_schemes": config.proxy_schemes,
            "proxy_path": config.proxy_path,
            "request_format": config.request_format,
            "response_format": config.response_format,
            "associate_plugin": config.associate_plugin,
            "is_options_request": config.is_options_request,
            "is_head_request": config.is_head_request,
            "define_date_format": config.define_date_format,
            "return_total_count": config.return_total_count,
            "enable_pagination": config.enable_pagination,
            "max_query_count": config.max_query_count,
            "enable_rate_limit": config.enable_rate_limit,
            "timeout_seconds": config.timeout_seconds,
            "proxy_auth": config.proxy_auth,
            "encryption_method": config.encryption_method,
            "enable_replay_protection": config.enable_replay_protection,
            "enable_whitelist": config.enable_whitelist,
            "whitelist_ips": config.whitelist_ips or "",
            "enable_blacklist": config.enable_blacklist,
            "blacklist_ips": config.blacklist_ips or "",
            "enable_audit_log": config.enable_audit_log,
            # 跨域设置
            "enable_cors": config.enable_cors or False,
            "cors_allow_origin": config.cors_allow_origin or "",
            "cors_expose_headers": config.cors_expose_headers or "",
            "cors_max_age": config.cors_max_age,
            "cors_allow_methods": config.cors_allow_methods or "",
            "cors_allow_headers": config.cors_allow_headers or "",
            "cors_allow_credentials": config.cors_allow_credentials if config.cors_allow_credentials is not None else True,
            "request_parameters": saved_request_parameters,
            "response_parameters": response_parameters,
            # 获取保存的响应头
            "response_headers": response_headers_list,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取接口配置详情失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口配置详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建接口配置"""
    try:
        # 验证数据库配置是否存在
        database_config_id = config_data.get("database_config_id")
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == database_config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not db_config:
            raise HTTPException(status_code=400, detail="数据库配置不存在")
        
        # 验证必需字段
        proxy_path = config_data.get("proxy_path")
        interface_name = config_data.get("interface_name")
        
        if not proxy_path or not proxy_path.strip():
            raise HTTPException(status_code=400, detail="代理路径不能为空")
        
        if not interface_name or not interface_name.strip():
            raise HTTPException(status_code=400, detail="接口名称不能为空")
        
        # 创建接口配置
        config = InterfaceConfig(
            user_id=current_user.id,
            database_config_id=config_data.get("database_config_id"),
            interface_name=config_data.get("interface_name"),
            interface_description=config_data.get("interface_description"),
            usage_instructions=config_data.get("usage_instructions"),
            category=config_data.get("category"),
            status=config_data.get("status", "draft"),
            entry_mode=config_data.get("entry_mode", "expert"),
            sql_statement=config_data.get("sql_statement"),
            table_name=config_data.get("table_name"),
            selected_fields=config_data.get("selected_fields"),
            where_conditions=config_data.get("where_conditions"),
            order_by_fields=config_data.get("order_by_fields"),
            sync_to_gateway=config_data.get("sync_to_gateway", False),
            extension_fields=config_data.get("extension_fields"),
            http_method=config_data.get("http_method", "GET"),
            proxy_schemes=config_data.get("proxy_schemes", "http"),
            proxy_path=config_data.get("proxy_path"),
            request_format=config_data.get("request_format", "application/json"),
            response_format=config_data.get("response_format", "application/json"),
            associate_plugin=config_data.get("associate_plugin", False),
            is_options_request=config_data.get("is_options_request", False),
            is_head_request=config_data.get("is_head_request", False),
            define_date_format=config_data.get("define_date_format", False),
            return_total_count=config_data.get("return_total_count", False),
            enable_pagination=config_data.get("enable_pagination", False),
            max_query_count=config_data.get("max_query_count", 10),
            enable_rate_limit=config_data.get("enable_rate_limit", False),
            timeout_seconds=config_data.get("timeout_seconds", 10),
            proxy_auth=config_data.get("proxy_auth", "no_auth"),
            encryption_method=config_data.get("encryption_method", "no_encryption"),
            enable_replay_protection=config_data.get("enable_replay_protection", False),
            enable_whitelist=config_data.get("enable_whitelist", False),
            whitelist_ips=config_data.get("whitelist_ips", ""),
            enable_blacklist=config_data.get("enable_blacklist", False),
            blacklist_ips=config_data.get("blacklist_ips", ""),
            enable_audit_log=config_data.get("enable_audit_log", False),
            # 跨域设置
            enable_cors=config_data.get("enable_cors", False),
            cors_allow_origin=config_data.get("cors_allow_origin", ""),
            cors_expose_headers=config_data.get("cors_expose_headers", ""),
            cors_max_age=config_data.get("cors_max_age"),
            cors_allow_methods=config_data.get("cors_allow_methods", ""),
            cors_allow_headers=config_data.get("cors_allow_headers", ""),
            cors_allow_credentials=config_data.get("cors_allow_credentials", True)
        )
        
        db.add(config)
        db.flush()  # 先刷新以获取config.id
        
        # 处理请求参数（如果提供了）
        if "request_parameters" in config_data and isinstance(config_data["request_parameters"], list):
            # 先删除旧的参数
            # 软删除旧的参数
            db.query(InterfaceParameter).filter(
                InterfaceParameter.interface_config_id == config.id,
                InterfaceParameter.is_deleted == False
            ).update({"is_deleted": True}, synchronize_session=False)
            # 创建新的参数
            for param_data in config_data["request_parameters"]:
                if isinstance(param_data, dict) and param_data.get("name"):
                    param = InterfaceParameter(
                        interface_config_id=config.id,
                        name=param_data.get("name"),
                        type=param_data.get("type", "string"),
                        description=param_data.get("description"),
                        constraint=param_data.get("constraint", "optional"),
                        location=param_data.get("location", "query"),
                        default_value=param_data.get("default_value")
                    )
                    db.add(param)
        
        # 处理响应头（HTTP Response Headers）
        if "response_headers" in config_data and isinstance(config_data["response_headers"], list):
            # 先删除旧的响应头（使用InterfaceHeader表，但需要区分类型）
            # 这里我们使用InterfaceHeader表存储响应头，通过name字段区分
            try:
                # 使用synchronize_session=False避免加载对象到会话
                # 软删除旧的响应头
                deleted_count = db.query(InterfaceHeader).filter(
                    InterfaceHeader.interface_config_id == config.id,
                    InterfaceHeader.name.like("Response-%"),  # 响应头使用Response-前缀
                    InterfaceHeader.is_deleted == False
                ).update({"is_deleted": True}, synchronize_session=False)
            except Exception as e:
                # 如果删除失败（可能是表结构问题），记录日志但继续
                logger.warning("删除旧响应头失败（可能不存在）: {}", e)
            # 创建新的响应头
            headers_added = 0
            for header_data in config_data["response_headers"]:
                if isinstance(header_data, dict) and header_data.get("name"):
                    try:
                        header = InterfaceHeader(
                            interface_config_id=config.id,
                            header_type="response",  # 响应头类型
                            attribute="",  # 属性字段
                            name=f"Response-{header_data.get('name')}",  # 添加前缀区分响应头
                            value=header_data.get("value", ""),
                            description=header_data.get("description", "HTTP响应头")
                        )
                        db.add(header)
                        headers_added += 1
                    except Exception as e:
                        logger.error("添加响应头失败: {}", e)
                        raise
        
        db.commit()
        db.refresh(config)
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={"id": config.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("创建接口配置失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建接口配置失败: {str(e)}"
        )


@router.put("/{config_id}", response_model=ResponseModel)
async def update_config(
    config_id: int,
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新接口配置"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 更新字段（排除需要特殊处理的字段）
        exclude_keys = {"request_parameters", "response_headers"}
        for key, value in config_data.items():
            if key not in exclude_keys and hasattr(config, key):
                setattr(config, key, value)
        
        # 处理请求参数（如果提供了）
        if "request_parameters" in config_data and isinstance(config_data["request_parameters"], list):
            # 先删除旧的参数
            # 软删除旧的参数
            db.query(InterfaceParameter).filter(
                InterfaceParameter.interface_config_id == config_id,
                InterfaceParameter.is_deleted == False
            ).update({"is_deleted": True}, synchronize_session=False)
            # 创建新的参数
            for param_data in config_data["request_parameters"]:
                if isinstance(param_data, dict) and param_data.get("name"):
                    param = InterfaceParameter(
                        interface_config_id=config_id,
                        name=param_data.get("name"),
                        type=param_data.get("type", "string"),
                        description=param_data.get("description"),
                        constraint=param_data.get("constraint", "optional"),
                        location=param_data.get("location", "query"),
                        default_value=param_data.get("default_value")
                    )
                    db.add(param)
        
        # 处理响应头（HTTP Response Headers）
        if "response_headers" in config_data and isinstance(config_data["response_headers"], list):
            # 先删除旧的响应头
            # 软删除旧的响应头
            db.query(InterfaceHeader).filter(
                InterfaceHeader.interface_config_id == config_id,
                InterfaceHeader.name.like("Response-%"),
                InterfaceHeader.is_deleted == False
            ).update({"is_deleted": True}, synchronize_session=False)
            # 创建新的响应头
            headers_added = 0
            for header_data in config_data["response_headers"]:
                if isinstance(header_data, dict) and header_data.get("name"):
                    header = InterfaceHeader(
                        interface_config_id=config_id,
                        header_type="response",  # 响应头类型
                        attribute="",  # 属性字段
                        name=f"Response-{header_data.get('name')}",
                        value=header_data.get("value", ""),
                        description=header_data.get("description", "HTTP响应头")
                    )
                    db.add(header)
                    headers_added += 1
        
        db.commit()
        db.refresh(config)
        
        return ResponseModel(
            success=True,
            message="更新成功",
            data={"id": config.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("更新接口配置失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新接口配置失败: {str(e)}"
        )


@router.delete("/{config_id}", response_model=ResponseModel)
async def delete_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除接口配置"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        if config.is_deleted:
            raise HTTPException(status_code=404, detail="接口配置已被删除")
        
        # 软删除关联的参数和请求头
        try:
            # 使用synchronize_session=False避免加载对象到会话
            updated_params = db.query(InterfaceParameter).filter(
                InterfaceParameter.interface_config_id == config_id,
                InterfaceParameter.is_deleted == False
            ).update({"is_deleted": True}, synchronize_session=False)
            updated_headers = db.query(InterfaceHeader).filter(
                InterfaceHeader.interface_config_id == config_id,
                InterfaceHeader.is_deleted == False
            ).update({"is_deleted": True}, synchronize_session=False)
            logger.info(f"软删除接口配置 {config_id} 的关联数据: {updated_params} 个参数, {updated_headers} 个请求头/响应头")
            db.flush()  # 确保删除操作被提交到数据库
        except Exception as e:
            logger.warning("软删除关联数据时出现警告（可能不存在）: {}", e)
            # 即使删除关联数据失败，也继续删除主配置
        
        # 软删除接口配置
        config.is_deleted = True
        db.commit()
        logger.info(f"成功软删除接口配置 {config_id}")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # 使用 logger.exception 或 {} 占位符避免格式化错误
        logger.exception("删除接口配置失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除接口配置失败: {str(e)}"
        )


@router.get("/{config_id}/samples", response_model=ResponseModel)
async def get_interface_samples(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取接口的入参出参样例数据"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 生成请求参数样例
        request_sample = {}
        if config.entry_mode == "expert" and config.sql_statement:
            parsed = parse_sql_parameters(config.sql_statement)
            for param in parsed.get("request_parameters", []):
                param_name = param.get("name")
                param_type = param.get("type", "string")
                if param_type == "integer":
                    request_sample[param_name] = 1
                elif param_type == "number":
                    request_sample[param_name] = 1.0
                elif param_type == "boolean":
                    request_sample[param_name] = True
                else:
                    request_sample[param_name] = "示例值"
        
        # 如果启用了分页，添加分页参数到样例
        if config.enable_pagination:
            request_sample["pageNumber"] = 1
            request_sample["pageSize"] = 10
        elif config.entry_mode == "graphical" and config.where_conditions:
            for cond in config.where_conditions:
                if cond.get("value_type") == "variable" and cond.get("variable_name"):
                    request_sample[cond.get("variable_name")] = "示例值"
        
        # 生成响应样例（基于字段信息）
        response_data = {
            "data": [],
            "count": 0,
            "pageNumber": 1,
            "pageSize": 10
        }
        if config.return_total_count:
            response_data["total"] = 0
        
        response_sample = {
            "success": True,
            "message": "success",
            "data": response_data
        }
        
        if config.entry_mode == "graphical" and config.selected_fields:
            # 图形模式：根据选择的字段生成样例数据
            sample_row = {}
            for field in config.selected_fields[:5]:  # 只显示前5个字段
                sample_row[field] = "示例值"
            response_sample["data"]["data"] = [sample_row]
            response_sample["data"]["count"] = 1
            if config.enable_pagination and config.return_total_count:
                response_sample["data"]["total"] = 1
        
        return ResponseModel(
            success=True,
            message="获取样例数据成功",
            data={
                "request_sample": request_sample,
                "response_sample": response_sample
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取接口样例数据失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口样例数据失败: {str(e)}"
        )


@router.get("/{config_id}/api-doc", response_model=ResponseModel)
async def get_interface_api_doc(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """生成接口的API文档"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id,
            InterfaceConfig.is_deleted == False
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
        
        # 获取请求参数和响应参数
        request_parameters = []
        response_parameters = []
        
        if config.entry_mode == "expert" and config.sql_statement:
            parsed = parse_sql_parameters(config.sql_statement)
            request_parameters = parsed.get("request_parameters", [])
            response_parameters = parsed.get("response_parameters", [])
        elif config.entry_mode == "graphical":
            # 图形模式：从WHERE条件中提取请求参数
            if config.where_conditions:
                for cond in config.where_conditions:
                    if cond.get("value_type") == "variable" and cond.get("variable_name"):
                        request_parameters.append({
                            "name": cond.get("variable_name"),
                            "type": "string",
                            "description": cond.get("description", ""),
                            "constraint": "required" if cond.get("required", True) else "optional",
                            "location": "query"
                        })
            # 图形模式：从selected_fields中提取响应参数（数据字段）
            if config.selected_fields:
                for field in config.selected_fields:
                    response_parameters.append({
                        "name": field,
                        "type": "string",  # 默认类型，实际类型可以从数据库schema获取
                        "description": f"字段 {field}",
                        "constraint": "required"
                    })
        
        # 如果启用了分页，添加分页参数到请求参数
        if config.enable_pagination:
            request_parameters.append({
                "name": "pageNumber",
                "type": "integer",
                "description": "页码，从1开始",
                "constraint": "optional",
                "location": "query"
            })
            request_parameters.append({
                "name": "pageSize",
                "type": "integer",
                "description": "每页数量，最大1000",
                "constraint": "optional",
                "location": "query"
            })
        
        # 获取服务器地址和端口（从环境变量或请求头获取）
        from app.core.config import settings
        
        if settings.API_SERVER_HOST:
            # 优先使用环境变量配置的服务器IP
            hostname = settings.API_SERVER_HOST
            scheme = settings.API_SERVER_SCHEME
        else:
            # 从请求头获取
            host_header = request.headers.get("host") if request else None
            if host_header:
                # 从host header中提取主机名（去掉端口）
                hostname = host_header.split(":")[0] if ":" in host_header else host_header
                scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
            else:
                # 使用默认配置
                hostname = settings.HOST if settings.HOST != "0.0.0.0" else "localhost"
                scheme = config.proxy_schemes or "http"
        
        api_port = settings.API_SERVER_PORT
        base_url = f"{scheme}://{hostname}:{api_port}"
        
        # 确保路径以/api开头
        proxy_path = config.proxy_path if config.proxy_path.startswith("/") else f"/{config.proxy_path}"
        if not proxy_path.startswith("/api"):
            proxy_path = f"/api{proxy_path}"
        
        # 构建API文档
        api_doc = {
            "title": config.interface_name,
            "description": config.interface_description or "无描述",
            "method": config.http_method,
            "path": proxy_path,
            "base_url": base_url,
            "full_url": f"{base_url}{proxy_path}",
            "request": {
                "method": config.http_method,
                "headers": {
                    "Content-Type": config.request_format
                },
                "parameters": request_parameters,
                "sample": {}
            },
            "response_parameters": response_parameters,
            "response": {
                "format": config.response_format,
                "parameters": response_parameters,  # 使用解析出的数据字段
                "sample": {
                    "success": True,
                    "message": "success",
                    "data": {
                        "data": [],
                        "count": 0,
                        "pageNumber": 1,
                        "pageSize": 10
                    } | ({"total": 0} if config.return_total_count else {})
                }
            },
            "pagination": {
                "enabled": config.enable_pagination,
                "page_param": "page",
                "page_size_param": "page_size"
            },
            "authentication": {
                "required": config.proxy_auth != "no_auth",
                "type": config.proxy_auth
            }
        }
        
        # 生成请求样例
        for param in request_parameters:
            param_name = param.get("name")
            param_type = param.get("type", "string")
            # 分页参数使用默认值
            if param_name == "pageNumber":
                api_doc["request"]["sample"][param_name] = 1
            elif param_name == "pageSize":
                api_doc["request"]["sample"][param_name] = 10
            elif param_type == "integer":
                api_doc["request"]["sample"][param_name] = 1
            elif param_type == "number":
                api_doc["request"]["sample"][param_name] = 1.0
            elif param_type == "boolean":
                api_doc["request"]["sample"][param_name] = True
            else:
                api_doc["request"]["sample"][param_name] = "示例值"
        
        # 生成响应样例
        if config.entry_mode == "graphical" and config.selected_fields:
            sample_row = {}
            for field in config.selected_fields[:5]:
                sample_row[field] = "示例值"
            api_doc["response"]["sample"]["data"]["data"] = [sample_row]
            api_doc["response"]["sample"]["data"]["count"] = 1
            api_doc["response"]["sample"]["data"]["total"] = 1
        
        return ResponseModel(
            success=True,
            message="生成API文档成功",
            data=api_doc
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("生成API文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成API文档失败: {str(e)}"
        )

