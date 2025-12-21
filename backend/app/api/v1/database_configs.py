"""
数据库配置路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, date
from app.core.database import get_local_db
from app.models import User, DatabaseConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.db_factory import DatabaseConnectionFactory
from app.core.sql_dialect import SQLDialectFactory
from app.core.password_encryption import encrypt_password, decrypt_password, is_encrypted
from loguru import logger
from sqlalchemy import text, inspect


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
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取数据库配置列表（支持分页）"""
    try:
        query = db.query(DatabaseConfig).filter(
            DatabaseConfig.user_id == current_user.id
        ).order_by(DatabaseConfig.created_at.desc())
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        configs = query.offset(offset).limit(page_size).all()
        
        result = []
        for config in configs:
            try:
                created_at_str = config.created_at.isoformat() if config.created_at else None
                updated_at_str = config.updated_at.isoformat() if config.updated_at else None
            except Exception:
                created_at_str = None
                updated_at_str = None
            
            # 密码遮掩显示
            password_display = "******" if config.password else ""
            
            result.append({
                "id": config.id,
                "name": config.name,
                "db_type": getattr(config, "db_type", "mysql"),  # 支持新字段，默认mysql
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "username": config.username,
                "password": password_display,  # 遮掩密码
                "charset": config.charset,
                "extra_params": getattr(config, "extra_params", None),  # 支持新字段
                "is_active": config.is_active,
                "created_at": created_at_str,
                "updated_at": updated_at_str
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result,
            pagination={
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取数据库配置列表失败: {}", e, exc_info=True)
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
        
        # 密码遮掩显示
        password_display = "******" if config.password else ""
        
        result = {
            "id": config.id,
            "name": config.name,
            "db_type": getattr(config, "db_type", "mysql"),  # 支持新字段，默认mysql
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "password": password_display,  # 遮掩密码
            "charset": config.charset,
            "extra_params": getattr(config, "extra_params", None),  # 支持新字段
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
        logger.error("获取数据库配置详情失败: {}", e, exc_info=True)
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
        # 加密密码
        password = config_data.get("password", "")
        encrypted_password = encrypt_password(password) if password else ""
        
        # 清理输入数据（去除首尾空格）
        host = config_data.get("host", "").strip() if config_data.get("host") else ""
        database = config_data.get("database", "").strip() if config_data.get("database") else ""
        username = config_data.get("username", "").strip() if config_data.get("username") else ""
        
        config = DatabaseConfig(
            user_id=current_user.id,
            name=config_data.get("name"),
            db_type=config_data.get("db_type", "mysql"),  # 支持新字段，默认mysql
            host=host,
            port=config_data.get("port", 3306),
            database=database,
            username=username,
            password=encrypted_password,  # 存储加密后的密码
            charset=config_data.get("charset", "utf8mb4"),
            extra_params=config_data.get("extra_params"),  # 支持新字段
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
        logger.error("创建数据库配置失败: {}", e, exc_info=True)
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
                # 如果是密码字段，需要加密
                if key == "password" and value:
                    setattr(config, key, encrypt_password(value))
                # 清理 host、database、username 字段的首尾空格
                elif key in ["host", "database", "username"] and value:
                    setattr(config, key, value.strip() if isinstance(value, str) else value)
                else:
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
        logger.error("更新数据库配置失败: {}", e, exc_info=True)
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
        logger.error("删除数据库配置失败: {}", e, exc_info=True)
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
        # 获取数据库类型，默认为mysql
        db_type = config_data.get("db_type", "mysql")
        
        # 安全：记录测试连接请求（不包含密码）
        safe_config_data = {k: v for k, v in config_data.items() if k != "password"}
        logger.info(f"用户 {current_user.id} 测试数据库连接: {safe_config_data}")
        
        # 对于SQLite，只需要database字段（文件路径）
        if db_type == "sqlite":
            database = config_data.get("database")
            if not database:
                raise HTTPException(status_code=400, detail="SQLite数据库文件路径不能为空")
        else:
            host = config_data.get("host")
            # 清理 hostname 中的空格
            if host:
                host = host.strip()
            
            port = config_data.get("port")
            database = config_data.get("database")
            username = config_data.get("username")
            password = config_data.get("password", "")
            
            if not all([host, database, username]):
                raise HTTPException(status_code=400, detail="主机、数据库名和用户名不能为空")
            
            # 如果没有指定端口，使用默认端口
            if not port:
                port = DatabaseConnectionFactory.get_default_port(db_type) or 3306
        
        # 创建临时配置对象用于测试
        from app.models import DatabaseConfig
        temp_config = DatabaseConfig(
            db_type=db_type,
            host=host if db_type != "sqlite" else "",
            port=port if db_type != "sqlite" else None,
            database=database,
            username=config_data.get("username", "").strip() if config_data.get("username") else "",
            password=password,
            charset=config_data.get("charset", "utf8mb4"),
            extra_params=config_data.get("extra_params")
        )
        
        try:
            # 使用工厂创建引擎
            engine = DatabaseConnectionFactory.create_engine(temp_config)
            # 获取测试SQL
            test_sql = DatabaseConnectionFactory.get_test_sql(db_type)
            with engine.connect() as conn:
                conn.execute(text(test_sql))
            engine.dispose()
            
            # 测试成功后，自动将配置设置为已激活
            config.is_active = True
            db.commit()
            
            return ResponseModel(
                success=True,
                message="连接成功"
            )
        except Exception as e:
            # 安全：记录错误时不包含密码信息
            logger.error("数据库连接测试失败 (用户: {}, 数据库类型: {}, 主机: {}): {}", 
                        current_user.id, db_type, config_data.get("host", "N/A") if 'config_data' in locals() else config.host if 'config' in locals() else "N/A", str(e), exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str or "authentication failed" in error_str.lower():
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                db_client_ip = ip_match.group(1) if ip_match else "未知"
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"数据库服务器看到的客户端IP: {db_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {db_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {db_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str or "connection timeout" in error_str.lower():
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str or "database" in error_str.lower() and "does not exist" in error_str.lower():
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
        # 安全：记录错误时不包含密码信息
        logger.error("测试数据库连接失败 (用户: {}): {}", current_user.id, str(e), exc_info=True)
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
        
        db_type = config.db_type or "mysql"
        
        # 安全：记录测试连接请求（不包含密码）
        logger.info(f"用户 {current_user.id} 测试数据库配置 {config_id} ({config.name}, {db_type})")
        
        try:
            # 使用工厂创建引擎
            engine = DatabaseConnectionFactory.create_engine(config)
            # 获取测试SQL
            test_sql = DatabaseConnectionFactory.get_test_sql(db_type)
            with engine.connect() as conn:
                conn.execute(text(test_sql))
            engine.dispose()
            
            # 测试成功后，自动将配置设置为已激活
            config.is_active = True
            db.commit()
            
            return ResponseModel(
                success=True,
                message="连接成功"
            )
        except Exception as e:
            # 安全：记录错误时不包含密码信息
            logger.error("数据库连接测试失败 (用户: {}, 数据库类型: {}, 主机: {}): {}", 
                        current_user.id, db_type, config_data.get("host", "N/A") if 'config_data' in locals() else config.host if 'config' in locals() else "N/A", str(e), exc_info=True)
            
            # 解析错误信息，提供更友好的提示
            error_str = str(e)
            if "Access denied" in error_str or "1045" in error_str or "authentication failed" in error_str.lower():
                import re
                ip_match = re.search(r"@'([^']+)'", error_str)
                db_client_ip = ip_match.group(1) if ip_match else "未知"
                current_client_ip = get_client_ip(request)
                
                detail_msg = f"数据库访问被拒绝。\n\n" \
                            f"数据库服务器看到的客户端IP: {db_client_ip}\n" \
                            f"当前请求的客户端IP: {current_client_ip}\n\n" \
                            f"可能原因：\n" \
                            f"1) 密码错误\n" \
                            f"2) IP地址 {db_client_ip} 不在数据库白名单中\n\n" \
                            f"解决方案：\n" \
                            f"请联系数据库管理员，将IP地址 {db_client_ip} 添加到数据库白名单中。"
            elif "timed out" in error_str or "2003" in error_str or "connection timeout" in error_str.lower():
                detail_msg = f"数据库连接超时。请检查：1) 数据库地址是否正确；2) 网络是否通畅；3) 防火墙设置。"
            elif "Unknown database" in error_str or "1049" in error_str or "database" in error_str.lower() and "does not exist" in error_str.lower():
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
        # 安全：记录错误时不包含密码信息
        logger.error("测试数据库连接失败 (用户: {}): {}", current_user.id, str(e), exc_info=True)
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
        
        db_type = config.db_type or "mysql"
        adapter = SQLDialectFactory.get_adapter(db_type)
        
        try:
            # 使用工厂创建引擎
            engine = DatabaseConnectionFactory.create_engine(config)
            
            # 根据数据库类型使用不同的方式获取表列表
            with engine.connect() as conn:
                if db_type == "sqlite":
                    # SQLite使用特殊方式获取表列表
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                    table_names = [row[0] for row in result]
                elif db_type == "postgresql":
                    # PostgreSQL需要指定schema，默认使用public schema
                    # 先尝试使用inspect获取（推荐方式）
                    table_names = []
                    try:
                        # 确保连接已建立
                        inspector = inspect(engine)
                        # 获取public schema的表列表
                        table_names = inspector.get_table_names(schema='public')
                        logger.info(f"PostgreSQL通过inspect获取到 {len(table_names)} 个表")
                        if table_names:
                            logger.debug(f"表列表: {table_names}")
                        else:
                            logger.warning("PostgreSQL inspect返回空列表，可能是schema中没有表或权限问题")
                    except Exception as e:
                        logger.warning("使用inspect获取PostgreSQL表列表失败: {}", e, exc_info=True)
                    
                    # 如果inspect获取不到或结果为空，使用SQL查询
                    if not table_names:
                        logger.info("PostgreSQL inspect结果为空，使用SQL查询获取表列表")
                        try:
                            # 使用适配器的查询方法
                            query = adapter.get_table_names_query(schema='public')
                            logger.debug(f"执行PostgreSQL查询: {query}")
                            result = conn.execute(text(query))
                            
                            # 确保正确获取表名
                            table_names = []
                            for row in result:
                                # 处理不同的返回格式
                                try:
                                    table_name = None
                                    # SQLAlchemy 2.0+ Row对象
                                    if hasattr(row, '_mapping'):
                                        table_name = row._mapping.get('table_name')
                                    # 尝试通过索引访问
                                    if not table_name and hasattr(row, '__getitem__'):
                                        try:
                                            table_name = row[0]
                                        except (IndexError, KeyError):
                                            pass
                                    # 尝试通过迭代获取第一个元素
                                    if not table_name and hasattr(row, '__iter__') and not isinstance(row, str):
                                        try:
                                            table_name = next(iter(row), None)
                                        except:
                                            pass
                                    # 最后尝试转换为字符串
                                    if not table_name:
                                        table_name = str(row) if row else None
                                    
                                    if table_name:
                                        table_name_str = str(table_name).strip()
                                        if table_name_str:
                                            table_names.append(table_name_str)
                                except Exception as e3:
                                    logger.warning("解析PostgreSQL查询结果行失败: {}, row: {}", e3, row)
                                    continue
                            
                            logger.info(f"PostgreSQL通过SQL查询获取到 {len(table_names)} 个表: {table_names}")
                        except Exception as e2:
                            logger.error("PostgreSQL SQL查询也失败: {}", e2, exc_info=True)
                            # 最后尝试：直接查询pg_tables
                            try:
                                logger.info("尝试使用pg_tables系统表查询")
                                result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
                                table_names = []
                                for row in result:
                                    if row and len(row) > 0:
                                        table_name = row[0] if isinstance(row, (tuple, list)) else str(row)
                                        table_names.append(str(table_name))
                                logger.info(f"通过pg_tables获取到 {len(table_names)} 个表: {table_names}")
                            except Exception as e3:
                                logger.error("使用pg_tables查询也失败: {}", e3, exc_info=True)
                                table_names = []
                elif db_type == "sqlserver":
                    # SQL Server使用inspect
                    table_names = []
                    try:
                        inspector = inspect(engine)
                        table_names = inspector.get_table_names()
                        logger.info(f"SQL Server通过inspect获取到 {len(table_names)} 个表")
                        if table_names:
                            logger.debug(f"表列表: {table_names[:10]}")
                    except Exception as e:
                        logger.warning("使用inspect获取SQL Server表列表失败，尝试使用SQL查询: {}", e)
                        try:
                            query = adapter.get_table_names_query()
                            result = conn.execute(text(query))
                            table_names = []
                            for row in result:
                                if hasattr(row, '_mapping'):
                                    table_name = row._mapping.get('table_name') or (row[0] if len(row) > 0 else None)
                                elif hasattr(row, '__getitem__'):
                                    table_name = row[0]
                                else:
                                    table_name = str(row) if row else None
                                if table_name:
                                    table_names.append(str(table_name))
                            logger.info(f"SQL Server通过SQL查询获取到 {len(table_names)} 个表: {table_names}")
                        except Exception as e2:
                            logger.error("SQL Server SQL查询也失败: {}", e2, exc_info=True)
                            table_names = []
                elif db_type == "oracle":
                    # Oracle使用inspect
                    table_names = []
                    try:
                        inspector = inspect(engine)
                        table_names = inspector.get_table_names()
                        logger.info(f"Oracle通过inspect获取到 {len(table_names)} 个表")
                        if table_names:
                            logger.debug(f"表列表: {table_names[:10]}")
                        else:
                            logger.warning("Oracle inspect返回空列表，可能是用户没有表或权限问题")
                    except Exception as e:
                        logger.warning("使用inspect获取Oracle表列表失败: {}", e, exc_info=True)
                        # 尝试使用SQL查询
                        try:
                            query = adapter.get_table_names_query()
                            result = conn.execute(text(query))
                            table_names = []
                            for row in result:
                                if hasattr(row, '_mapping'):
                                    table_name = row._mapping.get('table_name') or (row[0] if len(row) > 0 else None)
                                elif hasattr(row, '__getitem__'):
                                    table_name = row[0]
                                else:
                                    table_name = str(row) if row else None
                                if table_name:
                                    table_names.append(str(table_name))
                            logger.info(f"Oracle通过SQL查询获取到 {len(table_names)} 个表: {table_names}")
                        except Exception as e2:
                            logger.error("Oracle SQL查询也失败: {}", e2, exc_info=True)
                            table_names = []
                else:
                    # MySQL和其他数据库使用inspect
                    inspector = inspect(engine)
                    table_names = inspector.get_table_names()
            
            engine.dispose()
            
            # 确保返回的是列表
            if not isinstance(table_names, list):
                table_names = list(table_names) if table_names else []
            
            # 记录最终结果
            logger.info(f"数据库类型: {db_type}, 最终返回 {len(table_names)} 个表")
            if table_names:
                logger.debug(f"表名列表: {table_names[:10]}...")  # 只记录前10个
            
            return ResponseModel(
                success=True,
                message="获取成功",
                data=table_names
            )
        except Exception as e:
            logger.error("获取表列表失败: {}", e, exc_info=True)
            
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
        logger.error("获取表列表失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )


@router.get("/{config_id}/tables/{table_name}/sample", response_model=ResponseModel)
async def get_table_sample(
    config_id: int,
    table_name: str,
    limit: int = Query(10, ge=1, le=100, description="返回行数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取表的示例数据"""
    try:
        config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.user_id == current_user.id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="数据库配置不存在")
        
        db_type = config.db_type or "mysql"
        
        try:
            engine = DatabaseConnectionFactory.create_engine(config)
            
            with engine.connect() as conn:
                # 使用探查适配器获取示例数据查询
                from app.core.probe.database_adapters import (
                    MySQLAdapter, PostgreSQLAdapter, SQLServerAdapter,
                    OracleAdapter, SQLiteAdapter
                )
                
                adapters = {
                    "mysql": MySQLAdapter,
                    "postgresql": PostgreSQLAdapter,
                    "sqlserver": SQLServerAdapter,
                    "oracle": OracleAdapter,
                    "sqlite": SQLiteAdapter,
                }
                
                adapter_class = adapters.get(db_type.lower())
                if not adapter_class:
                    raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {db_type}")
                
                adapter = adapter_class()
                
                # 获取示例数据查询
                if db_type == "postgresql":
                    sample_query = adapter.get_sample_data_query(config.database, table_name, schema_name="public", limit=limit)
                else:
                    sample_query = adapter.get_sample_data_query(config.database, table_name, limit=limit)
                
                result = conn.execute(text(sample_query))
                rows = result.fetchall()
                
                # 转换为字典列表
                if rows:
                    # 获取列名
                    if hasattr(result, 'keys'):
                        columns = list(result.keys())
                    else:
                        # 如果没有keys方法，使用索引
                        columns = [f"column_{i}" for i in range(len(rows[0]))]
                    
                    sample_data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i] if isinstance(row, (tuple, list)) else getattr(row, col, None)
                            # 处理特殊类型
                            if value is None:
                                row_dict[col] = None
                            elif isinstance(value, (datetime, date)):
                                row_dict[col] = value.isoformat()
                            else:
                                row_dict[col] = str(value)
                        sample_data.append(row_dict)
                    
                    return ResponseModel(
                        success=True,
                        message="获取成功",
                        data=sample_data
                    )
                else:
                    return ResponseModel(
                        success=True,
                        message="表为空",
                        data=[]
                    )
            
        except Exception as e:
            logger.error("获取示例数据失败: {}", e, exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=f"获取示例数据失败: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取示例数据失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取示例数据失败: {str(e)}"
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
        
        db_type = config.db_type or "mysql"
        adapter = SQLDialectFactory.get_adapter(db_type)
        
        try:
            # 使用工厂创建引擎
            engine = DatabaseConnectionFactory.create_engine(config)
            
            with engine.connect() as conn:
                # 对于SQLite，需要特殊处理
                if db_type == "sqlite":
                    # SQLite使用PRAGMA获取表信息
                    try:
                        pragma_result = conn.execute(text(f"PRAGMA table_info({adapter.escape_identifier(table_name)})"))
                        columns_info = []
                        primary_keys = []
                        
                        for row in pragma_result:
                            # PRAGMA table_info返回: cid, name, type, notnull, dflt_value, pk
                            cid = row[0]
                            col_name = row[1]
                            col_type = row[2]
                            notnull = row[3]
                            dflt_value = row[4]
                            pk = row[5]
                            
                            if pk:
                                primary_keys.append(col_name)
                            
                            columns_info.append({
                                "name": col_name,
                                "type": col_type,
                                "nullable": notnull == 0,
                                "default": str(dflt_value) if dflt_value is not None else None,
                                "autoincrement": False,  # SQLite需要检查AUTOINCREMENT关键字
                                "primary_key": pk == 1,
                                "comment": ""
                            })
                        
                        result = {
                            "name": table_name,
                            "columns": columns_info,
                            "primary_keys": primary_keys
                        }
                        
                        engine.dispose()
                        
                        return ResponseModel(
                            success=True,
                            message="获取成功",
                            data=result
                        )
                    except Exception as e:
                        logger.error(f"SQLite获取表信息失败: {e}", exc_info=True)
                        raise HTTPException(status_code=400, detail=f"获取SQLite表信息失败: {str(e)}")
                
                # 其他数据库使用inspect
                inspector = inspect(engine)
                
                # 获取列信息
                try:
                    columns = inspector.get_columns(table_name)
                except Exception as e:
                    logger.error(f"获取列信息失败: {e}", exc_info=True)
                    raise HTTPException(status_code=400, detail=f"获取表列信息失败: {str(e)}")
                
                # 获取主键
                try:
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    primary_keys = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                except Exception as e:
                    logger.warning(f"获取主键信息失败: {e}")
                    primary_keys = []
                
                # 获取字段注释（根据数据库类型）
                comment_map = {}
                if db_type == "mysql":
                    try:
                        comment_query = text("""
                            SELECT COLUMN_NAME, COLUMN_COMMENT 
                            FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = :db_name 
                            AND TABLE_NAME = :table_name
                        """)
                        comment_result = conn.execute(comment_query, {"db_name": config.database, "table_name": table_name})
                        comment_map = {row[0]: row[1] for row in comment_result if row[1]}
                    except Exception as e:
                        logger.warning(f"获取MySQL字段注释失败: {e}")
                elif db_type == "postgresql":
                    # PostgreSQL可以使用pg_description获取注释
                    try:
                        comment_query = text("""
                            SELECT a.attname as column_name, 
                                   d.description as column_comment
                            FROM pg_attribute a
                            JOIN pg_class c ON a.attrelid = c.oid
                            JOIN pg_namespace n ON c.relnamespace = n.oid
                            LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
                            WHERE c.relname = :table_name 
                            AND n.nspname = 'public'
                            AND a.attnum > 0
                            AND NOT a.attisdropped
                        """)
                        comment_result = conn.execute(comment_query, {"table_name": table_name})
                        comment_map = {row[0]: row[1] for row in comment_result if row[1]}
                    except Exception as e:
                        logger.warning(f"获取PostgreSQL字段注释失败: {e}")
                # 对于其他数据库，可以在这里添加获取注释的逻辑
            
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
            logger.error("获取表信息失败: {}", e, exc_info=True)
            
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
        logger.error("获取表信息失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表信息失败: {str(e)}"
        )

