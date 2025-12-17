"""
数据库配置路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from database import get_local_db
from models import User, DatabaseConfig
from schemas import ResponseModel
from auth import get_current_active_user
from loguru import logger
from sqlalchemy import create_engine, text, inspect
from urllib.parse import quote_plus


def get_client_ip(request: Request) -> str:
    """获取客户端真实IP地址"""
    # 优先从X-Forwarded-For获取（如果经过代理）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For可能包含多个IP，取第一个
        return forwarded_for.split(",")[0].strip()
    
    # 从X-Real-IP获取（如果使用nginx等反向代理）
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 直接从客户端获取
    if request.client:
        return request.client.host
    
    return "未知"

router = APIRouter(prefix="/api/v1/database-configs", tags=["数据库配置"])


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_configs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据库配置列表"""
    try:
        configs = db.query(DatabaseConfig).filter(
            DatabaseConfig.user_id == current_user.id
        ).order_by(DatabaseConfig.created_at.desc()).all()
        
        result = []
        for config in configs:
            try:
                created_at_str = config.created_at.isoformat() if config.created_at else None
                updated_at_str = config.updated_at.isoformat() if config.updated_at else None
            except Exception:
                created_at_str = None
                updated_at_str = None
            
            result.append({
                "id": config.id,
                "name": config.name,
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "username": config.username,
                "charset": config.charset,
                "is_active": config.is_active,
                "created_at": created_at_str,
                "updated_at": updated_at_str
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据库配置列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库配置列表失败: {str(e)}"
        )


@router.get("/{config_id}", response_model=ResponseModel)
async def get_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据库配置详情"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        result = {
            "id": config.id,
            "name": config.name,
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "charset": config.charset,
            "is_active": config.is_active,
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
        logger.error(f"获取数据库配置详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库配置详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建数据库配置"""
    try:
        config = DatabaseConfig(
            user_id=current_user.id,
            name=config_data.get("name"),
            host=config_data.get("host"),
            port=config_data.get("port", 3306),
            database=config_data.get("database"),
            username=config_data.get("username"),
            password=config_data.get("password"),
            charset=config_data.get("charset", "utf8mb4"),
            is_active=config_data.get("is_active", True)
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={"id": config.id}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"创建数据库配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建数据库配置失败: {str(e)}"
        )


@router.put("/{config_id}", response_model=ResponseModel)
async def update_config(
    config_id: int,
    config_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新数据库配置"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 更新字段
        for key, value in config_data.items():
            if hasattr(config, key) and key != "id":
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
        logger.error(f"更新数据库配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新数据库配置失败: {str(e)}"
        )


@router.delete("/{config_id}", response_model=ResponseModel)
async def delete_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除数据库配置"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
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
        logger.error(f"删除数据库配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除数据库配置失败: {str(e)}"
        )


# 注意：/test 路由必须在 /{config_id}/test 之前定义，否则会被误匹配
@router.post("/test", response_model=ResponseModel)
async def test_connection_direct(
    request: Request,
    config_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """直接测试数据库连接（不需要保存配置）"""
    try:
        host = config_data.get("host")
        port = config_data.get("port", 3306)
        database = config_data.get("database")
        username = config_data.get("username")
        password = config_data.get("password", "")
        charset = config_data.get("charset", "utf8mb4")
        
        if not all([host, database, username]):
            raise HTTPException(status_code=400, detail="主机、数据库名和用户名不能为空")
        
        # 构建连接URL - 使用quote_plus正确编码密码中的特殊字符
        encoded_password = quote_plus(password) if password else ""
        encoded_username = quote_plus(username) if username else ""
        db_url = f"mysql+pymysql://{encoded_username}:{encoded_password}@{host}:{port}/{database}?charset={charset}"
        
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            
            return ResponseModel(
                success=True,
                message="连接成功"
            )
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}", exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str:
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                mysql_client_ip = ip_match.group(1) if ip_match else "未知"
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"MySQL服务器看到的客户端IP: {mysql_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {mysql_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {mysql_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str:
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str:
                detail_msg = f"数据库不存在。请检查数据库名称是否正确。"
            else:
                detail_msg = f"连接失败: {error_str}"
            
            raise HTTPException(
                status_code=400,
                detail=detail_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试数据库连接失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试连接失败: {str(e)}"
        )


@router.post("/{config_id}/test", response_model=ResponseModel)
async def test_connection(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """测试已保存的数据库配置连接"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 构建连接URL - 使用quote_plus正确编码密码中的特殊字符
        encoded_password = quote_plus(config.password) if config.password else ""
        encoded_username = quote_plus(config.username) if config.username else ""
        db_url = f"mysql+pymysql://{encoded_username}:{encoded_password}@{config.host}:{config.port}/{config.database}?charset={config.charset or 'utf8mb4'}"
        
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            
            return ResponseModel(
                success=True,
                message="连接成功"
            )
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}", exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str:
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                mysql_client_ip = ip_match.group(1) if ip_match else "未知"
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"MySQL服务器看到的客户端IP: {mysql_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {mysql_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {mysql_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str:
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str:
                detail_msg = f"数据库不存在。请检查数据库名称是否正确。"
            else:
                detail_msg = f"连接失败: {error_str}"
            
            raise HTTPException(
                status_code=400,
                detail=detail_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试数据库连接失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试连接失败: {str(e)}"
        )


@router.get("/{config_id}/tables", response_model=ResponseModel)
async def list_tables(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据库表列表"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 构建连接URL - 使用quote_plus正确编码密码中的特殊字符
        encoded_password = quote_plus(config.password) if config.password else ""
        encoded_username = quote_plus(config.username) if config.username else ""
        db_url = f"mysql+pymysql://{encoded_username}:{encoded_password}@{config.host}:{config.port}/{config.database}?charset={config.charset or 'utf8mb4'}"
        
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            # 先建立连接，再使用inspect
            with engine.connect() as conn:
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
            
            engine.dispose()
            
            return ResponseModel(
                success=True,
                message="获取成功",
                data=table_names
            )
        except Exception as e:
            logger.error(f"获取表列表失败: {e}", exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str:
                # 提取MySQL服务器看到的客户端IP（从错误信息中）
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                mysql_client_ip = ip_match.group(1) if ip_match else "未知"
                
                # 获取当前请求的客户端IP
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"MySQL服务器看到的客户端IP: {mysql_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {mysql_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {mysql_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str:
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str:
                detail_msg = f"数据库不存在。请检查数据库名称是否正确。"
            else:
                detail_msg = f"获取表列表失败: {error_str}"
            
            raise HTTPException(
                status_code=400,
                detail=detail_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )


@router.get("/{config_id}/tables/{table_name}/info", response_model=ResponseModel)
async def get_table_info(
    config_id: int,
    table_name: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取表信息（字段、主键等）"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        # 构建连接URL - 使用quote_plus正确编码密码中的特殊字符
        encoded_password = quote_plus(config.password) if config.password else ""
        encoded_username = quote_plus(config.username) if config.username else ""
        db_url = f"mysql+pymysql://{encoded_username}:{encoded_password}@{config.host}:{config.port}/{config.database}?charset={config.charset or 'utf8mb4'}"
        
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            # 先建立连接，再使用inspect
            with engine.connect() as conn:
                inspector = inspect(engine)
                
                # 获取列信息
                columns = inspector.get_columns(table_name)
                # 获取主键
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                
                # 获取字段注释（COMMENT）
                comment_query = text(f"""
                    SELECT COLUMN_NAME, COLUMN_COMMENT 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = :db_name 
                    AND TABLE_NAME = :table_name
                """)
                comment_result = conn.execute(comment_query, {"db_name": config.database, "table_name": table_name})
                comment_map = {row[0]: row[1] for row in comment_result if row[1]}
            
            # 转换列信息为可序列化格式
            columns_info = []
            for col in columns:
                col_info = {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default", "")) if col.get("default") is not None else None,
                    "autoincrement": col.get("autoincrement", False),
                    "primary_key": col["name"] in primary_keys,
                    "comment": comment_map.get(col["name"], "")  # 添加字段注释
                }
                columns_info.append(col_info)
            
            engine.dispose()
            
            result = {
                "name": table_name,
                "columns": columns_info,
                "primary_keys": primary_keys
            }
            
            return ResponseModel(
                success=True,
                message="获取成功",
                data=result
            )
        except Exception as e:
            logger.error(f"获取表信息失败: {e}", exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str:
                # 提取MySQL服务器看到的客户端IP（从错误信息中）
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                mysql_client_ip = ip_match.group(1) if ip_match else "未知"
                
                # 获取当前请求的客户端IP
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"MySQL服务器看到的客户端IP: {mysql_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {mysql_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {mysql_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str:
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str:
                detail_msg = f"数据库不存在。请检查数据库名称是否正确。"
            else:
                detail_msg = f"获取表信息失败: {error_str}"
            
            raise HTTPException(
                status_code=400,
                detail=detail_msg
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表信息失败: {str(e)}"
        )

