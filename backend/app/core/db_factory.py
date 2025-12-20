"""
数据库连接工厂
支持多种数据库类型的连接创建和URL生成
"""
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from urllib.parse import quote_plus
from typing import Optional, Dict, Any
import threading
from app.models import DatabaseConfig
from app.core.password_encryption import decrypt_password
from loguru import logger


class DatabaseConnectionFactory:
    """数据库连接工厂类"""
    
    # 支持的数据库类型及其默认端口
    SUPPORTED_TYPES = {
        "mysql": {"default_port": 3306, "driver": "pymysql"},
        "postgresql": {"default_port": 5432, "driver": "psycopg2"},
        "sqlite": {"default_port": None, "driver": None},
        "sqlserver": {"default_port": 1433, "driver": "pyodbc"},
        "oracle": {"default_port": 1521, "driver": "cx_oracle"},
    }
    
    # 引擎缓存（线程安全）
    _engine_cache: Dict[str, Engine] = {}
    _cache_lock = threading.Lock()
    
    @classmethod
    def _get_cache_key(cls, db_config: DatabaseConfig) -> str:
        """
        生成缓存键（基于数据库配置的唯一标识）
        
        Args:
            db_config: 数据库配置对象
            
        Returns:
            缓存键字符串
        """
        # 使用配置ID和连接URL的组合作为缓存键
        # 如果配置ID存在，使用ID；否则使用连接URL的哈希
        if hasattr(db_config, 'id') and db_config.id:
            return f"db_config_{db_config.id}"
        else:
            # 使用连接URL作为缓存键
            db_url = cls.get_connection_url(db_config)
            import hashlib
            url_hash = hashlib.md5(db_url.encode('utf-8')).hexdigest()
            return f"db_url_{url_hash}"
    
    @classmethod
    def get_connection_url(cls, db_config: DatabaseConfig) -> str:
        """
        根据数据库配置生成连接URL
        
        Args:
            db_config: 数据库配置对象
            
        Returns:
            数据库连接URL字符串
        """
        db_type = (db_config.db_type or "mysql").lower()
        
        if db_type not in cls.SUPPORTED_TYPES:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        if db_type == "sqlite":
            # SQLite使用文件路径，不需要host/port/user/password
            # database字段存储文件路径
            file_path = db_config.database
            if not file_path.startswith("/"):
                # 相对路径
                file_path = f"./{file_path}"
            return f"sqlite:///{file_path}"
        
        # 解密密码（如果已加密）
        plain_password = decrypt_password(db_config.password) if db_config.password else ""
        
        # 编码用户名和密码中的特殊字符
        encoded_username = quote_plus(db_config.username) if db_config.username else ""
        encoded_password = quote_plus(plain_password) if plain_password else ""
        
        # 构建基础连接URL
        if db_type == "mysql":
            # MySQL: mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
            charset = db_config.charset or "utf8mb4"
            url = f"mysql+pymysql://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.database}?charset={charset}"
            
        elif db_type == "postgresql":
            # PostgreSQL: postgresql+psycopg2://user:pass@host:port/db
            url = f"postgresql+psycopg2://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.database}"
            
        elif db_type == "sqlserver":
            # SQL Server: mssql+pyodbc://user:pass@host:port/db?driver=ODBC+Driver+17+for+SQL+Server
            # 注意：SQL Server需要ODBC驱动
            driver = "ODBC+Driver+17+for+SQL+Server"
            if db_config.extra_params and isinstance(db_config.extra_params, dict):
                driver = db_config.extra_params.get("driver", driver)
            encoded_driver = quote_plus(driver)
            url = f"mssql+pyodbc://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.database}?driver={encoded_driver}"
            
        elif db_type == "oracle":
            # Oracle: oracle+cx_oracle://user:pass@host:port/?service_name=service
            # 或者使用SID: oracle+cx_oracle://user:pass@host:port/?sid=sid
            service_name = db_config.database
            if db_config.extra_params and isinstance(db_config.extra_params, dict):
                if "service_name" in db_config.extra_params:
                    service_name = db_config.extra_params["service_name"]
                elif "sid" in db_config.extra_params:
                    url = f"oracle+cx_oracle://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/?sid={db_config.extra_params['sid']}"
                    return url
            
            url = f"oracle+cx_oracle://{encoded_username}:{encoded_password}@{db_config.host}:{db_config.port}/?service_name={service_name}"
            
        else:
            raise ValueError(f"未实现的数据库类型: {db_type}")
        
        # 添加额外连接参数
        if db_config.extra_params and isinstance(db_config.extra_params, dict):
            params = []
            for key, value in db_config.extra_params.items():
                # 跳过已经在URL中使用的参数
                if key in ["driver", "service_name", "sid"]:
                    continue
                if value is not None:
                    params.append(f"{key}={quote_plus(str(value))}")
            if params:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}{'&'.join(params)}"
        
        return url
    
    @classmethod
    def create_engine(cls, db_config: DatabaseConfig, **engine_kwargs) -> Engine:
        """
        根据数据库配置创建SQLAlchemy引擎（带缓存机制）
        
        Args:
            db_config: 数据库配置对象
            **engine_kwargs: 额外的引擎参数（如pool_size, pool_recycle等）
            
        Returns:
            SQLAlchemy引擎对象
        """
        # 生成缓存键
        cache_key = cls._get_cache_key(db_config)
        
        # 检查缓存
        with cls._cache_lock:
            if cache_key in cls._engine_cache:
                cached_engine = cls._engine_cache[cache_key]
                # 验证引擎是否仍然有效
                try:
                    # 尝试连接以验证引擎是否有效
                    with cached_engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.debug(f"使用缓存的数据库引擎: {cache_key}")
                    return cached_engine
                except Exception as e:
                    # 引擎无效，从缓存中移除
                    logger.warning(f"缓存的引擎无效，将重新创建: {e}")
                    try:
                        cached_engine.dispose()
                    except Exception:
                        pass
                    del cls._engine_cache[cache_key]
        
        # 缓存未命中或引擎无效，创建新引擎
        db_url = cls.get_connection_url(db_config)
        db_type = (db_config.db_type or "mysql").lower()
        
        # 默认引擎参数
        default_kwargs = {
            "pool_pre_ping": True,  # 连接前检查连接是否有效
            "pool_recycle": 3600,    # 1小时后回收连接
            "echo": False,            # 不打印SQL语句
        }
        
        # 从配置中获取连接池参数（如果可用）
        from app.core.config import settings
        default_pool_size = getattr(settings, 'DB_POOL_SIZE', 10)
        default_max_overflow = getattr(settings, 'DB_MAX_OVERFLOW', 20)
        default_pool_recycle = getattr(settings, 'DB_POOL_RECYCLE', 3600)
        
        # 根据数据库类型设置特定参数
        if db_type == "mysql":
            default_kwargs.update({
                "pool_size": default_pool_size,
                "max_overflow": default_max_overflow,
                "pool_recycle": default_pool_recycle,
                "connect_args": {
                    "connect_timeout": 15,
                    "read_timeout": 30,
                    "write_timeout": 30,
                }
            })
        elif db_type == "postgresql":
            default_kwargs.update({
                "pool_size": default_pool_size,
                "max_overflow": default_max_overflow,
                "pool_recycle": default_pool_recycle,
                "connect_args": {
                    "connect_timeout": 10,
                }
            })
        elif db_type == "sqlite":
            default_kwargs.update({
                "pool_size": 1,  # SQLite不支持连接池
                "max_overflow": 0,
                "connect_args": {
                    "check_same_thread": False,  # SQLite允许多线程
                }
            })
        elif db_type == "sqlserver":
            default_kwargs.update({
                "pool_size": default_pool_size,
                "max_overflow": default_max_overflow,
                "pool_recycle": default_pool_recycle,
            })
        elif db_type == "oracle":
            default_kwargs.update({
                "pool_size": default_pool_size,
                "max_overflow": default_max_overflow,
                "pool_recycle": default_pool_recycle,
            })
        
        # 合并用户提供的参数
        default_kwargs.update(engine_kwargs)
        
        try:
            engine = create_engine(db_url, **default_kwargs)
            logger.debug(f"创建数据库引擎成功: {db_type} - {db_config.name}")
            
            # 缓存引擎
            with cls._cache_lock:
                cls._engine_cache[cache_key] = engine
                logger.debug(f"数据库引擎已缓存: {cache_key} (当前缓存数量: {len(cls._engine_cache)})")
            
            return engine
        except Exception as e:
            logger.error(f"创建数据库引擎失败: {db_type} - {db_config.name} - {e}", exc_info=True)
            raise
    
    @classmethod
    def clear_engine_cache(cls, db_config: Optional[DatabaseConfig] = None):
        """
        清理引擎缓存
        
        Args:
            db_config: 如果提供，只清理该配置的引擎；否则清理所有引擎
        """
        with cls._cache_lock:
            if db_config:
                cache_key = cls._get_cache_key(db_config)
                if cache_key in cls._engine_cache:
                    try:
                        cls._engine_cache[cache_key].dispose()
                    except Exception as e:
                        logger.warning(f"释放引擎时出错: {e}")
                    del cls._engine_cache[cache_key]
                    logger.info(f"已清理数据库引擎缓存: {cache_key}")
            else:
                # 清理所有引擎
                count = len(cls._engine_cache)
                for engine in cls._engine_cache.values():
                    try:
                        engine.dispose()
                    except Exception:
                        pass
                cls._engine_cache.clear()
                logger.info(f"已清理所有数据库引擎缓存 (共 {count} 个)")
    
    @classmethod
    def get_cache_size(cls) -> int:
        """
        获取当前缓存的引擎数量
        
        Returns:
            缓存的引擎数量
        """
        with cls._cache_lock:
            return len(cls._engine_cache)
    
    @classmethod
    def create_session(cls, db_config: DatabaseConfig, **engine_kwargs) -> Session:
        """
        根据数据库配置创建数据库会话
        
        Args:
            db_config: 数据库配置对象
            **engine_kwargs: 额外的引擎参数
            
        Returns:
            SQLAlchemy会话对象
        """
        engine = cls.create_engine(db_config, **engine_kwargs)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    @classmethod
    def get_test_sql(cls, db_type: str) -> str:
        """
        获取测试连接的SQL语句（不同数据库的测试SQL不同）
        
        Args:
            db_type: 数据库类型
            
        Returns:
            测试SQL语句
        """
        db_type = db_type.lower() if db_type else "mysql"
        
        test_sql_map = {
            "mysql": "SELECT 1",
            "postgresql": "SELECT 1",
            "sqlite": "SELECT 1",
            "sqlserver": "SELECT 1",
            "oracle": "SELECT 1 FROM DUAL",
        }
        
        return test_sql_map.get(db_type, "SELECT 1")
    
    @classmethod
    def is_supported(cls, db_type: str) -> bool:
        """
        检查数据库类型是否支持
        
        Args:
            db_type: 数据库类型
            
        Returns:
            是否支持
        """
        return db_type.lower() in cls.SUPPORTED_TYPES
    
    @classmethod
    def get_default_port(cls, db_type: str) -> Optional[int]:
        """
        获取数据库类型的默认端口
        
        Args:
            db_type: 数据库类型
            
        Returns:
            默认端口号，如果不存在则返回None
        """
        db_type = db_type.lower() if db_type else "mysql"
        type_info = cls.SUPPORTED_TYPES.get(db_type)
        return type_info["default_port"] if type_info else None


