"""
API文档生成路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette.requests import Request
from fastapi.responses import Response, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_local_db
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.models import User, InterfaceConfig, DatabaseConfig
from loguru import logger
import json
from datetime import datetime
from app.core.config import settings

router = APIRouter(prefix="/api/v1/api-docs", tags=["API文档"])


def generate_curl_example(config: InterfaceConfig, full_url: str, request_sample: dict, auth_type: str) -> str:
    """生成cURL示例命令"""
    method = config.http_method.upper()
    
    # 构建查询参数
    query_params = []
    for key, value in request_sample.items():
        if isinstance(value, str):
            query_params.append(f"{key}={value}")
        else:
            query_params.append(f"{key}={json.dumps(value)}")
    
    query_string = "&".join(query_params)
    url_with_params = f"{full_url}?{query_string}" if query_string else full_url
    
    # 构建cURL命令
    curl_cmd = f"curl -X {method} '{url_with_params}'"
    
    # 添加认证头
    if auth_type == "bearer":
        curl_cmd += " -H 'Authorization: Bearer YOUR_TOKEN'"
    elif auth_type == "basic":
        curl_cmd += " -H 'Authorization: Basic YOUR_CREDENTIALS'"
    
    # 添加Content-Type
    if method in ["POST", "PUT", "PATCH"]:
        curl_cmd += f" -H 'Content-Type: {config.request_format}'"
        if request_sample:
            curl_cmd += f" -d '{json.dumps(request_sample)}'"
    
    return curl_cmd


async def get_full_interface_doc(
    config: InterfaceConfig,
    db_config: DatabaseConfig,
    request: Request,
    current_user: User,
    db: Session
) -> Dict[str, Any]:
    """获取完整的接口文档信息（包含所有元数据）"""
    # 获取请求参数和样例数据
    from app.api.v1 import interface_configs as interface_configs_module
    parse_sql_parameters = interface_configs_module.parse_sql_parameters
    
    request_parameters = []
    response_parameters = []
    request_sample = {}
    response_sample = {
        "success": True,
        "message": "success",
        "data": {
            "data": [],
            "count": 0,
            "pageNumber": 1,
            "pageSize": 10
        }
    }
    
    # 如果启用了分页，添加total字段
    if config.return_total_count:
        response_sample["data"]["total"] = 0
    
    # 解析请求参数和响应参数
    if config.entry_mode == "expert" and config.sql_statement:
        parsed = parse_sql_parameters(config.sql_statement)
        request_parameters = parsed.get("request_parameters", [])
        response_parameters = parsed.get("response_parameters", [])
        for param in request_parameters:
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
                    request_sample[cond.get("variable_name")] = "示例值"
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
        request_sample["pageNumber"] = 1
        request_sample["pageSize"] = 10
    
    # 尝试实际执行接口获取真实响应数据作为示例
    try:
        from app.api.v1.interface_executor import execute_interface_sql
        real_result = execute_interface_sql(
            config,
            db_config,
            request_sample,
            page=1,
            page_size=1,
            client_ip=None,
            user_id=current_user.id
        )
        if real_result and isinstance(real_result, dict) and real_result.get("data") is not None:
            response_data = {
                "data": real_result.get("data", [])[:1],
                "count": len(real_result.get("data", [])[:1]),
                "pageNumber": real_result.get("pageNumber", 1),
                "pageSize": real_result.get("pageSize", 1)
            }
            if config.return_total_count:
                response_data["total"] = real_result.get("total", 0)
            response_sample["data"] = response_data
            
            # 从实际执行结果中提取响应参数（数据字段）
            if real_result.get("data") and len(real_result.get("data", [])) > 0:
                # 获取第一条数据的字段作为响应参数
                first_row = real_result.get("data", [])[0]
                if isinstance(first_row, dict):
                    # 如果响应参数为空（例如SELECT *的情况），从实际数据中提取
                    if not response_parameters:
                        for field_name in first_row.keys():
                            # 推断字段类型
                            field_value = first_row[field_name]
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
        logger.warning("获取真实响应数据失败，使用默认示例: {}", e)
        if config.entry_mode == "graphical" and config.selected_fields:
            sample_row = {}
            for field in config.selected_fields:
                sample_row[field] = "示例值"
            response_sample["data"]["data"] = [sample_row]
            response_sample["data"]["count"] = 1
            response_sample["data"]["total"] = 1
        elif config.entry_mode == "expert" and config.sql_statement:
            import re
            select_match = re.search(r'SELECT\s+(.+?)\s+FROM', config.sql_statement, re.IGNORECASE)
            if select_match:
                fields_str = select_match.group(1)
                if fields_str.strip() != "*":
                    fields = [f.strip().split()[0].strip('`') for f in fields_str.split(',')]
                    sample_row = {}
                    for field in fields[:10]:
                        sample_row[field] = "示例值"
                    response_sample["data"]["data"] = [sample_row]
                    response_sample["data"]["count"] = 1
                    if config.return_total_count:
                        response_sample["data"]["total"] = 1
    
    # 获取服务器地址和端口（从环境变量或请求头获取）
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
            scheme = "https" if (request and request.headers.get("x-forwarded-proto") == "https") else "http"
        else:
            hostname = settings.HOST if settings.HOST != "0.0.0.0" else "localhost"
            scheme = config.proxy_schemes or "http"
    
    # 使用配置的API端口
    api_port = settings.API_SERVER_PORT
    base_url = f"{scheme}://{hostname}:{api_port}"
    proxy_path = config.proxy_path if config.proxy_path.startswith("/") else f"/{config.proxy_path}"
    # 确保路径以/api开头
    if not proxy_path.startswith("/api"):
        proxy_path = f"/api{proxy_path}"
    full_url = f"{base_url}{proxy_path}"
    
    return {
        "id": config.id,
        "interface_name": config.interface_name,
        "interface_description": config.interface_description or "",
        "usage_instructions": config.usage_instructions or "",
        "database_name": db_config.name if db_config else "未知数据库",
        "http_method": config.http_method,
        "proxy_path": proxy_path,
        "base_url": base_url,
        "full_url": full_url,
        "proxy_schemes": config.proxy_schemes,
        "request_format": config.request_format,
        "response_format": config.response_format,
        "status": config.status,
        "entry_mode": config.entry_mode,
        "enable_pagination": config.enable_pagination,
        "max_query_count": config.max_query_count,
        "proxy_auth": config.proxy_auth,
        "timeout_seconds": config.timeout_seconds,
        "return_total_count": config.return_total_count,
        "enable_rate_limit": config.enable_rate_limit,
        "request_parameters": request_parameters,
        "response_parameters": response_parameters,
        "request_sample": request_sample,
        "response_sample": response_sample,
        "curl_example": generate_curl_example(config, full_url, request_sample, config.proxy_auth),
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None
    }


@router.get("/interfaces", response_model=ResponseModel)
async def list_interface_docs(
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取所有接口的文档列表（支持分页）"""
    try:
        query = db.query(InterfaceConfig).filter(
            InterfaceConfig.user_id == current_user.id
        )
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        configs = query.order_by(InterfaceConfig.created_at.desc()).offset(offset).limit(page_size).all()
        
        docs_list = []
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
            
            # 生成基础文档信息
            doc_info = {
                "id": config.id,
                "interface_name": config.interface_name,
                "interface_description": config.interface_description or "",
                "database_name": db_config.name if db_config else "未知数据库",
                "http_method": config.http_method,
                "proxy_path": config.proxy_path,
                "status": config.status,
                "entry_mode": config.entry_mode,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
            docs_list.append(doc_info)
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=docs_list,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except Exception as e:
        logger.error("获取接口文档列表失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口文档列表失败: {str(e)}"
        )


@router.get("/interfaces/{config_id}", response_model=ResponseModel)
async def get_interface_doc(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取单个接口的详细文档"""
    try:
        config = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == config_id,
            InterfaceConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="接口配置不存在")
        
        db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
        doc = await get_full_interface_doc(config, db_config, request, current_user, db)
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=doc
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取接口文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取接口文档失败: {str(e)}"
        )


@router.post("/generate-all", response_model=ResponseModel)
async def generate_all_docs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """生成所有接口的API文档"""
    try:
        configs = db.query(InterfaceConfig).filter(
            InterfaceConfig.user_id == current_user.id
        ).all()
        
        count = len(configs)
        return ResponseModel(
            success=True,
            message=f"成功生成 {count} 个接口的文档",
            data={"count": count}
        )
    except Exception as e:
        logger.error("生成文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成文档失败: {str(e)}"
        )


@router.get("/export/markdown")
async def export_markdown(
    interface_id: Optional[int] = Query(None, description="接口ID，不传则导出所有"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """导出Markdown格式文档"""
    try:
        if interface_id:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.id == interface_id,
                InterfaceConfig.user_id == current_user.id
            ).all()
        else:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.user_id == current_user.id
            ).all()
        
        content = f"# API接口文档\n\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
            doc = await get_full_interface_doc(config, db_config, request, current_user, db)
            
            content += f"## {doc['interface_name']}\n\n"
            content += f"**请求方式:** `{doc['http_method']}`\n\n"
            content += f"**接口路径:** `{doc['proxy_path']}`\n\n"
            content += f"**完整URL:** `{doc['full_url']}`\n\n"
            if doc['interface_description']:
                content += f"**描述:** {doc['interface_description']}\n\n"
            if doc['usage_instructions']:
                content += f"**使用说明:** {doc['usage_instructions']}\n\n"
            content += f"**数据库:** {doc['database_name']}\n\n"
            content += f"**状态:** {doc['status']}\n\n"
            content += f"**录入模式:** {doc['entry_mode']}\n\n"
            if doc['enable_pagination']:
                content += f"**分页:** 启用 (最大查询数量: {doc['max_query_count']})\n\n"
            if doc['proxy_auth'] != 'no_auth':
                content += f"**认证方式:** {doc['proxy_auth']}\n\n"
            if doc['timeout_seconds']:
                content += f"**超时时间:** {doc['timeout_seconds']}秒\n\n"
            if doc['created_at']:
                content += f"**创建时间:** {doc['created_at']}\n\n"
            if doc['updated_at']:
                content += f"**更新时间:** {doc['updated_at']}\n\n"
            
            # 请求参数
            if doc['request_parameters']:
                content += "### 请求参数\n\n"
                content += "| 参数名 | 类型 | 描述 | 约束 | 位置 |\n"
                content += "|--------|------|------|------|------|\n"
                for param in doc['request_parameters']:
                    content += f"| {param.get('name', '')} | {param.get('type', '')} | {param.get('description', '')} | {param.get('constraint', '')} | {param.get('location', '')} |\n"
                content += "\n"
            
            # 请求示例
            if doc['request_sample']:
                content += "### 请求示例\n\n"
                content += "```json\n"
                content += json.dumps(doc['request_sample'], indent=2, ensure_ascii=False)
                content += "\n```\n\n"
            
            # 响应参数
            if doc.get('response_parameters'):
                content += "### 响应参数\n\n"
                content += "| 参数名 | 类型 | 描述 | 约束 |\n"
                content += "|--------|------|------|------|\n"
                for param in doc['response_parameters']:
                    content += f"| {param.get('name', '')} | {param.get('type', '')} | {param.get('description', '')} | {param.get('constraint', '')} |\n"
                content += "\n"
            
            # 响应示例
            if doc['response_sample']:
                content += "### 响应示例\n\n"
                content += "```json\n"
                content += json.dumps(doc['response_sample'], indent=2, ensure_ascii=False)
                content += "\n```\n\n"
            
            # cURL示例
            if doc['curl_example']:
                content += "### cURL示例\n\n"
                content += "```bash\n"
                content += doc['curl_example']
                content += "\n```\n\n"
            
            content += "---\n\n"
        
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=api-docs-{datetime.now().strftime('%Y%m%d')}.md"}
        )
    except Exception as e:
        logger.error("导出Markdown文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出Markdown文档失败: {str(e)}"
        )


@router.get("/export/html")
async def export_html(
    interface_id: Optional[int] = Query(None, description="接口ID，不传则导出所有"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """导出HTML格式文档"""
    try:
        if interface_id:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.id == interface_id,
                InterfaceConfig.user_id == current_user.id
            ).all()
        else:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.user_id == current_user.id
            ).all()
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>API接口文档</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 3px solid #409eff; padding-bottom: 10px; }}
        h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 30px; }}
        h3 {{ color: #888; margin-top: 20px; }}
        .interface {{ margin-bottom: 40px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; background: #f9f9f9; }}
        .method {{ display: inline-block; padding: 5px 10px; background: #409eff; color: white; border-radius: 3px; font-weight: bold; }}
        .path {{ font-family: monospace; color: #666; }}
        .url {{ font-family: monospace; color: #409eff; word-break: break-all; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        pre {{ background: #282c34; color: #abb2bf; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        code {{ font-family: 'Courier New', monospace; }}
        .meta-info {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>API接口文档</h1>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
            doc = await get_full_interface_doc(config, db_config, request, current_user, db)
            
            html_content += f"""
    <div class="interface">
        <h2>{doc['interface_name']}</h2>
        <p><span class="method">{doc['http_method']}</span> <span class="path">{doc['proxy_path']}</span></p>
        <p><strong>完整URL:</strong> <span class="url">{doc['full_url']}</span></p>
        {f'<p class="meta-info"><strong>描述:</strong> {doc["interface_description"]}</p>' if doc['interface_description'] else ''}
        {f'<p class="meta-info"><strong>使用说明:</strong> {doc["usage_instructions"]}</p>' if doc['usage_instructions'] else ''}
        <p class="meta-info"><strong>数据库:</strong> {doc['database_name']}</p>
        <p class="meta-info"><strong>状态:</strong> {doc['status']}</p>
        <p class="meta-info"><strong>录入模式:</strong> {doc['entry_mode']}</p>
        {f'<p class="meta-info"><strong>分页:</strong> 启用 (最大查询数量: {doc["max_query_count"]})</p>' if doc['enable_pagination'] else ''}
        {f'<p class="meta-info"><strong>认证方式:</strong> {doc["proxy_auth"]}</p>' if doc['proxy_auth'] != 'no_auth' else ''}
        {f'<p class="meta-info"><strong>超时时间:</strong> {doc["timeout_seconds"]}秒</p>' if doc['timeout_seconds'] else ''}
        {f'<p class="meta-info"><strong>创建时间:</strong> {doc["created_at"]}</p>' if doc['created_at'] else ''}
        {f'<p class="meta-info"><strong>更新时间:</strong> {doc["updated_at"]}</p>' if doc['updated_at'] else ''}
"""
            
            # 请求参数
            if doc['request_parameters']:
                html_content += """
        <h3>请求参数</h3>
        <table>
            <thead>
                <tr>
                    <th>参数名</th>
                    <th>类型</th>
                    <th>描述</th>
                    <th>约束</th>
                    <th>位置</th>
                </tr>
            </thead>
            <tbody>
"""
                for param in doc['request_parameters']:
                    html_content += f"""
                <tr>
                    <td>{param.get('name', '')}</td>
                    <td>{param.get('type', '')}</td>
                    <td>{param.get('description', '')}</td>
                    <td>{param.get('constraint', '')}</td>
                    <td>{param.get('location', '')}</td>
                </tr>
"""
                html_content += """
            </tbody>
        </table>
"""
            
            # 请求示例
            if doc['request_sample']:
                html_content += """
        <h3>请求示例</h3>
        <pre><code>"""
                html_content += json.dumps(doc['request_sample'], indent=2, ensure_ascii=False)
                html_content += """</code></pre>
"""
            
            # 响应参数
            if doc.get('response_parameters'):
                html_content += """
        <h3>响应参数</h3>
        <table>
            <thead>
                <tr>
                    <th>参数名</th>
                    <th>类型</th>
                    <th>描述</th>
                    <th>约束</th>
                </tr>
            </thead>
            <tbody>
"""
                for param in doc['response_parameters']:
                    html_content += f"""
                <tr>
                    <td>{param.get('name', '')}</td>
                    <td>{param.get('type', '')}</td>
                    <td>{param.get('description', '')}</td>
                    <td>{param.get('constraint', '')}</td>
                </tr>
"""
                html_content += """
            </tbody>
        </table>
"""
            
            # 响应示例
            if doc['response_sample']:
                html_content += """
        <h3>响应示例</h3>
        <pre><code>"""
                html_content += json.dumps(doc['response_sample'], indent=2, ensure_ascii=False)
                html_content += """</code></pre>
"""
            
            # cURL示例
            if doc['curl_example']:
                html_content += """
        <h3>cURL示例</h3>
        <pre><code>"""
                html_content += doc['curl_example']
                html_content += """</code></pre>
"""
            
            html_content += """
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=api-docs-{datetime.now().strftime('%Y%m%d')}.html"}
        )
    except Exception as e:
        logger.error("导出HTML文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出HTML文档失败: {str(e)}"
        )


@router.get("/export/openapi")
async def export_openapi(
    interface_id: Optional[int] = Query(None, description="接口ID，不传则导出所有"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """导出OpenAPI格式文档"""
    try:
        if interface_id:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.id == interface_id,
                InterfaceConfig.user_id == current_user.id
            ).all()
        else:
            configs = db.query(InterfaceConfig).filter(
                InterfaceConfig.user_id == current_user.id
            ).all()
        
        # 获取服务器地址
        host_header = request.headers.get("host") if request else None
        if host_header:
            host = host_header
            scheme = "https" if (request and request.headers.get("x-forwarded-proto") == "https") else "http"
        else:
            host = f"{settings.HOST}:{settings.PORT}" if settings.HOST != "0.0.0.0" else f"localhost:{settings.PORT}"
            scheme = "http"
        base_url = f"{scheme}://{host}"
        
        openapi_doc = {
            "openapi": "3.0.1",
            "info": {
                "title": "表转服务API文档",
                "version": "1.0.0",
                "description": "自动生成的API接口文档",
                "contact": {
                    "name": "API Support"
                }
            },
            "servers": [
                {
                    "url": base_url,
                    "description": "API服务器"
                }
            ],
            "paths": {}
        }
        
        for config in configs:
            db_config = db.query(DatabaseConfig).filter(DatabaseConfig.id == config.database_config_id).first()
            doc = await get_full_interface_doc(config, db_config, request, current_user, db)
            
            path = doc['proxy_path']
            method = doc['http_method'].lower()
            
            if path not in openapi_doc["paths"]:
                openapi_doc["paths"][path] = {}
            
            # 构建参数
            parameters = []
            for param in doc['request_parameters']:
                param_schema = {"type": param.get('type', 'string')}
                if param.get('type') == 'integer':
                    param_schema = {"type": "integer"}
                elif param.get('type') == 'number':
                    param_schema = {"type": "number"}
                elif param.get('type') == 'boolean':
                    param_schema = {"type": "boolean"}
                
                parameters.append({
                    "name": param.get('name'),
                    "in": param.get('location', 'query'),
                    "required": param.get('constraint') == 'required',
                    "description": param.get('description', ''),
                    "schema": param_schema
                })
            
            # 构建响应schema
            response_data_properties = {
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "数据列表"
                },
                "count": {
                    "type": "integer",
                    "example": 1,
                    "description": "当前页返回的数据条数"
                },
                "pageNumber": {
                    "type": "integer",
                    "example": 1,
                    "description": "当前页码"
                },
                "pageSize": {
                    "type": "integer",
                    "example": 10,
                    "description": "每页数量"
                }
            }
            
            # 如果启用了返回总数，添加total字段
            if doc.get('enable_pagination') and doc.get('return_total_count'):
                response_data_properties["total"] = {
                    "type": "integer",
                    "example": 100,
                    "description": "数据总数"
                }
            
            operation = {
                "summary": doc['interface_name'],
                "description": doc['interface_description'] or "无描述",
                "tags": [doc['database_name']],
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "成功",
                        "content": {
                            doc['response_format']: {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean", "example": True},
                                        "message": {"type": "string", "example": "success"},
                                        "data": {
                                            "type": "object",
                                            "properties": response_data_properties
                                        }
                                    }
                                },
                                "example": doc['response_sample']
                            }
                        }
                    }
                }
            }
            
            # 添加请求体（POST/PUT/PATCH）
            if method in ['post', 'put', 'patch'] and doc['request_sample']:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        doc['request_format']: {
                            "schema": {
                                "type": "object",
                                "properties": {k: {"type": "string", "example": v} for k, v in doc['request_sample'].items()}
                            },
                            "example": doc['request_sample']
                        }
                    }
                }
            
            # 添加认证要求
            if doc['proxy_auth'] != 'no_auth':
                operation["security"] = []
                if doc['proxy_auth'] == 'bearer':
                    operation["security"].append({"bearerAuth": []})
                elif doc['proxy_auth'] == 'basic':
                    operation["security"].append({"basicAuth": []})
            
            openapi_doc["paths"][path][method] = operation
        
        # 添加安全定义
        if any(config.proxy_auth != "no_auth" for config in configs):
            openapi_doc["components"] = {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    },
                    "basicAuth": {
                        "type": "http",
                        "scheme": "basic"
                    }
                }
            }
        
        return JSONResponse(
            content=openapi_doc,
            headers={"Content-Disposition": f"attachment; filename=openapi-{datetime.now().strftime('%Y%m%d')}.json"}
        )
    except Exception as e:
        logger.error("导出OpenAPI文档失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出OpenAPI文档失败: {str(e)}"
        )


