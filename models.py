"""
数据模型定义
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    hashed_password = Column(String(255), nullable=False, comment="加密后的密码")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    database_configs = relationship("DatabaseConfig", back_populates="user", cascade="all, delete-orphan")
    interface_configs = relationship("InterfaceConfig", back_populates="user", cascade="all, delete-orphan")


class DatabaseConfig(Base):
    """数据库配置模型"""
    __tablename__ = "database_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    name = Column(String(100), nullable=False, comment="配置名称")
    host = Column(String(255), nullable=False, comment="数据库主机")
    port = Column(Integer, default=3306, comment="数据库端口")
    database = Column(String(100), nullable=False, comment="数据库名")
    username = Column(String(100), nullable=False, comment="数据库用户名")
    password = Column(String(255), nullable=False, comment="数据库密码")
    charset = Column(String(20), default="utf8mb4", comment="字符集")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="database_configs")
    interface_configs = relationship("InterfaceConfig", back_populates="database_config", cascade="all, delete-orphan")


class InterfaceConfig(Base):
    """接口配置模型"""
    __tablename__ = "interface_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    database_config_id = Column(Integer, ForeignKey("database_configs.id", ondelete="CASCADE"), nullable=False, comment="数据库配置ID")
    
    # 基本信息
    interface_name = Column(String(200), nullable=False, comment="接口名称")
    interface_description = Column(Text, comment="接口描述")
    usage_instructions = Column(Text, comment="使用说明")
    category = Column(String(100), comment="分类")
    status = Column(String(20), default="draft", comment="状态: draft/inactive/active")
    
    # 录入模式
    entry_mode = Column(String(20), nullable=False, comment="录入模式: expert/graphical")
    
    # 专家模式配置
    sql_statement = Column(Text, comment="SQL语句（专家模式）")
    
    # 图形模式配置
    table_name = Column(String(200), comment="表名（图形模式）")
    selected_fields = Column(JSON, comment="选择的字段列表（图形模式）")
    where_conditions = Column(JSON, comment="WHERE条件列表（图形模式）")
    order_by_fields = Column(JSON, comment="ORDER BY字段列表（图形模式）")
    
    # 代理接口配置
    sync_to_gateway = Column(Boolean, default=False, comment="是否同步到网关")
    extension_fields = Column(Text, comment="扩展字段")
    http_method = Column(String(10), default="GET", comment="HTTP方法")
    proxy_schemes = Column(String(20), default="http", comment="代理协议")
    proxy_path = Column(String(500), nullable=False, comment="代理路径")
    request_format = Column(String(50), default="application/json", comment="请求格式")
    response_format = Column(String(50), default="application/json", comment="响应格式")
    associate_plugin = Column(Boolean, default=False, comment="关联插件")
    is_options_request = Column(Boolean, default=False, comment="是否OPTIONS请求")
    is_head_request = Column(Boolean, default=False, comment="是否HEAD请求")
    define_date_format = Column(Boolean, default=False, comment="定义日期格式")
    
    # 跨域设置
    enable_cors = Column(Boolean, default=False, comment="开启系统跨域")
    cors_allow_origin = Column(String(500), comment="Access-Control-Allow-Origin")
    cors_expose_headers = Column(String(500), comment="Access-Control-Expose-Headers")
    cors_max_age = Column(Integer, comment="Access-Control-Max-Age（秒）")
    cors_allow_methods = Column(String(200), comment="Access-Control-Allow-Methods")
    cors_allow_headers = Column(String(500), comment="Access-Control-Allow-Headers")
    cors_allow_credentials = Column(Boolean, default=True, comment="Access-Control-Allow-Credentials")
    
    # 风险管控设置
    return_total_count = Column(Boolean, default=False, comment="返回总数")
    enable_pagination = Column(Boolean, default=False, comment="启用分页")
    max_query_count = Column(Integer, default=10, comment="最大查询数量")
    enable_rate_limit = Column(Boolean, default=False, comment="启用限流")
    timeout_seconds = Column(Integer, default=10, comment="超时时间（秒）")
    proxy_auth = Column(String(50), default="no_auth", comment="代理认证: no_auth/basic/digest/token/once")
    encryption_method = Column(String(50), default="no_encryption", comment="加密方法: no_encryption/sm4/des/aes")
    enable_replay_protection = Column(Boolean, default=False, comment="启用重放保护")
    enable_whitelist = Column(Boolean, default=False, comment="启用白名单")
    whitelist_ips = Column(Text, comment="白名单IP地址列表（换行分隔）")
    enable_blacklist = Column(Boolean, default=False, comment="启用黑名单")
    blacklist_ips = Column(Text, comment="黑名单IP地址列表（换行分隔）")
    enable_audit_log = Column(Boolean, default=False, comment="启用审计日志")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="interface_configs")
    database_config = relationship("DatabaseConfig", back_populates="interface_configs")
    parameters = relationship("InterfaceParameter", back_populates="interface_config", cascade="all, delete-orphan")
    headers = relationship("InterfaceHeader", back_populates="interface_config", cascade="all, delete-orphan")


class InterfaceParameter(Base):
    """接口参数模型"""
    __tablename__ = "interface_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    interface_config_id = Column(Integer, ForeignKey("interface_configs.id", ondelete="CASCADE"), nullable=False, comment="接口配置ID")
    name = Column(String(100), nullable=False, comment="参数名")
    type = Column(String(50), nullable=False, comment="参数类型")
    description = Column(Text, comment="参数描述")
    constraint = Column(String(50), default="optional", comment="约束: required/optional")
    location = Column(String(50), default="query", comment="位置: query/body/header/path")
    default_value = Column(Text, comment="默认值")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    interface_config = relationship("InterfaceConfig", back_populates="parameters")


class InterfaceHeader(Base):
    """接口请求头模型"""
    __tablename__ = "interface_headers"
    
    id = Column(Integer, primary_key=True, index=True)
    interface_config_id = Column(Integer, ForeignKey("interface_configs.id", ondelete="CASCADE"), nullable=False, comment="接口配置ID")
    header_type = Column(String(20), nullable=False, default="response", comment="请求头类型")
    attribute = Column(String(100), nullable=False, default="", comment="属性")
    name = Column(String(100), nullable=False, default="", comment="请求头名称")
    value = Column(String(500), nullable=True, comment="请求头值")
    description = Column(Text, comment="描述")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    interface_config = relationship("InterfaceConfig", back_populates="headers")

