"""
接口配置路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from database import get_local_db
from models import User, InterfaceConfig, InterfaceParameter, InterfaceHeader, DatabaseConfig
from schemas import ResponseModel
from auth import get_current_active_user
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
                for token in tokens:
                    if token.ttype is DML and token.value.upper() == 'SELECT':
                        in_select = True
                        continue
                    if in_select and isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            if isinstance(identifier, Identifier):
                                field_name = identifier.get_real_name()
                                response_params.append({
                                    "name": field_name,
                                    "type": "string",
                                    "description": f"字段 {field_name}"
                                })
                        break
        
        return {
            "request_parameters": request_params,
            "response_parameters": response_params
        }
    except Exception as e:
        logger.error(f"解析SQL参数失败: {e}", exc_info=True)
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
        logger.error(f"解析SQL失败: {e}", exc_info=True)
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
    page_size: Optional[int] = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取接口配置列表（支持分页）"""
    try:
        query = db.query(InterfaceConfig).filter(InterfaceConfig.user_id == current_user.id)
        
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
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
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
        logger.error(f"获取接口配置列表失败: {e}", exc_info=True)
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
            InterfaceConfig.user_id == current_user.id
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
        elif config.entry_mode == "graphical" and config.where_conditions:
            # 图形模式：从WHERE条件中提取参数
            for cond in config.where_conditions:
                if cond.get("value_type") == "variable" and cond.get("variable_name"):
                    request_parameters.append({
                        "name": cond.get("variable_name"),
                        "type": "string",
                        "description": cond.get("description", ""),
                        "constraint": "required" if cond.get("required", True) else "optional",
                        "location": "query"
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
            "request_parameters": request_parameters,
            "response_parameters": response_parameters,
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
        logger.error(f"获取接口配置详情失败: {e}", exc_info=True)
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
            enable_audit_log=config_data.get("enable_audit_log", False)
        )
        
        db.add(config)
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
        logger.error(f"创建接口配置失败: {e}", exc_info=True)
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
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 更新字段
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
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
        logger.error(f"更新接口配置失败: {e}", exc_info=True)
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
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        # 先删除关联的参数和请求头（级联删除应该自动处理，但为了确保安全，显式删除）
        try:
            from models import InterfaceParameter, InterfaceHeader
            # 使用synchronize_session=False避免加载对象到会话
            db.query(InterfaceParameter).filter(InterfaceParameter.interface_config_id == config_id).delete(synchronize_session=False)
            db.query(InterfaceHeader).filter(InterfaceHeader.interface_config_id == config_id).delete(synchronize_session=False)
        except Exception as e:
            logger.warning("删除关联数据时出现警告（可能不存在）: {}", e)
        
        # 删除接口配置
        db.delete(config)
        db.commit()
        
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
            InterfaceConfig.user_id == current_user.id
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
        elif config.entry_mode == "graphical" and config.where_conditions:
            for cond in config.where_conditions:
                if cond.get("value_type") == "variable" and cond.get("variable_name"):
                    request_sample[cond.get("variable_name")] = "示例值"
        
        # 生成响应样例（基于字段信息）
        response_sample = {
            "success": True,
            "message": "执行成功",
            "data": {
                "data": [],
                "count": 0,
                "total": 0,
                "page": 1,
                "page_size": 10
            }
        }
        
        if config.entry_mode == "graphical" and config.selected_fields:
            # 图形模式：根据选择的字段生成样例数据
            sample_row = {}
            for field in config.selected_fields[:5]:  # 只显示前5个字段
                sample_row[field] = "示例值"
            response_sample["data"]["data"] = [sample_row]
            response_sample["data"]["count"] = 1
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
        logger.error(f"获取接口样例数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口样例数据失败: {str(e)}"
        )


@router.get("/{config_id}/api-doc", response_model=ResponseModel)
async def get_interface_api_doc(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """生成接口的API文档"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
        
        # 获取请求参数
        request_parameters = []
        if config.entry_mode == "expert" and config.sql_statement:
            parsed = parse_sql_parameters(config.sql_statement)
            request_parameters = parsed.get("request_parameters", [])
        elif config.entry_mode == "graphical" and config.where_conditions:
            for cond in config.where_conditions:
                if cond.get("value_type") == "variable" and cond.get("variable_name"):
                    request_parameters.append({
                        "name": cond.get("variable_name"),
                        "type": "string",
                        "description": cond.get("description", ""),
                        "constraint": "required" if cond.get("required", True) else "optional",
                        "location": "query"
                    })
        
        # 构建API文档
        api_doc = {
            "title": config.interface_name,
            "description": config.interface_description or "无描述",
            "method": config.http_method,
            "path": config.proxy_path,
            "base_url": f"{config.proxy_schemes}://your-domain.com",
            "full_url": f"{config.proxy_schemes}://your-domain.com{config.proxy_path}",
            "request": {
                "method": config.http_method,
                "headers": {
                    "Content-Type": config.request_format
                },
                "parameters": request_parameters,
                "sample": {}
            },
            "response": {
                "format": config.response_format,
                "sample": {
                    "success": True,
                    "message": "执行成功",
                    "data": {
                        "data": [],
                        "count": 0,
                        "total": 0,
                        "page": 1,
                        "page_size": 10
                    }
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
            if param_type == "integer":
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
        logger.error(f"生成API文档失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成API文档失败: {str(e)}"
        )

