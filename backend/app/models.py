"""
数据模型定义
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# 尝试导入 pgvector 相关类型（如果可用）
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    # 如果 pgvector 不可用，使用 ARRAY 作为后备
    try:
        from sqlalchemy import ARRAY
        PGVECTOR_AVAILABLE = False
    except ImportError:
        ARRAY = None
        PGVECTOR_AVAILABLE = False


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
    # 智能问数相关关系
    chat_sessions = relationship("ChatSession", foreign_keys="ChatSession.user_id", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", foreign_keys="Dashboard.user_id", cascade="all, delete-orphan")
    probe_tasks = relationship("ProbeTask", foreign_keys="ProbeTask.user_id", cascade="all, delete-orphan")


class DatabaseConfig(Base):
    """数据库配置模型"""
    __tablename__ = "database_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    name = Column(String(100), nullable=False, comment="配置名称")
    # 数据库类型：mysql/postgresql/sqlite/sqlserver/oracle
    db_type = Column(String(50), default="mysql", nullable=False, comment="数据库类型")
    host = Column(String(255), nullable=False, comment="数据库主机")
    port = Column(Integer, default=3306, comment="数据库端口")
    database = Column(String(100), nullable=False, comment="数据库名")
    username = Column(String(100), nullable=False, comment="数据库用户名")
    password = Column(String(255), nullable=False, comment="数据库密码")
    charset = Column(String(20), default="utf8mb4", comment="字符集")
    # 额外连接参数（JSON格式，如SSL配置、连接池参数等）
    extra_params = Column(JSON, nullable=True, comment="额外连接参数（JSON格式）")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="database_configs")
    interface_configs = relationship("InterfaceConfig", back_populates="database_config", cascade="all, delete-orphan")
    probe_tasks = relationship("ProbeTask", foreign_keys="ProbeTask.database_config_id", cascade="all, delete-orphan")


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
    entry_mode = Column(String(20), nullable=False, comment="录入模式: expert/graphical/query (query为问数模式)")
    
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
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    
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
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
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
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    interface_config = relationship("InterfaceConfig", back_populates="headers")


# ==================== 智能问数功能相关模型 ====================

class AIModelConfig(Base):
    """AI模型配置模型"""
    __tablename__ = "ai_model_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模型名称（如：deepseek-chat, qwen-turbo）")
    provider = Column(String(50), nullable=False, comment="提供商（deepseek, qwen, kimi, openai等）")
    api_key = Column(Text, nullable=False, comment="API密钥（加密存储）")
    api_base_url = Column(String(500), nullable=True, comment="API基础URL")
    model_name = Column(String(100), nullable=False, comment="具体模型名称")
    max_tokens = Column(Integer, default=2000, comment="最大token数")
    temperature = Column(String(10), default="0.7", comment="温度参数")
    scene = Column(String(100), nullable=True, comment="使用场景（general/multimodal/code/math/agent/long_context/low_cost/enterprise/education/medical/legal/finance/government/industry/social/roleplay）")
    is_default = Column(Boolean, default=False, comment="是否默认模型")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'},
    )


class Terminology(Base):
    """术语库模型"""
    __tablename__ = "terminologies"
    
    id = Column(Integer, primary_key=True, index=True)
    business_term = Column(String(200), nullable=False, comment="业务术语（如：销售量）")
    db_field = Column(String(200), nullable=False, comment="数据库字段（如：sales_amount）")
    table_name = Column(String(200), nullable=True, comment="所属表名")
    description = Column(Text, nullable=True, comment="术语说明")
    category = Column(String(100), nullable=True, comment="分类")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    
    # 唯一约束：业务术语+数据库字段+表名组合唯一
    __table_args__ = (
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'},
    )


class SQLExample(Base):
    """SQL示例库模型"""
    __tablename__ = "sql_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="示例标题")
    question = Column(Text, nullable=False, comment="对应的问题（自然语言）")
    sql_statement = Column(Text, nullable=False, comment="SQL语句")
    db_type = Column(String(50), nullable=False, comment="数据库类型")
    table_name = Column(String(200), nullable=True, comment="涉及的表名")
    description = Column(Text, nullable=True, comment="示例说明")
    chart_type = Column(String(50), nullable=True, comment="推荐图表类型")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])


class CustomPrompt(Base):
    """自定义提示词模型"""
    __tablename__ = "custom_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="提示词名称")
    prompt_type = Column(String(50), nullable=False, comment="类型（sql_generation, data_analysis等）")
    content = Column(Text, nullable=False, comment="提示词内容")
    priority = Column(Integer, default=0, comment="优先级（数字越大优先级越高）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])


class BusinessKnowledge(Base):
    """业务知识库模型"""
    __tablename__ = "business_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="知识标题")
    content = Column(Text, nullable=False, comment="知识内容")
    category = Column(String(100), nullable=True, comment="分类")
    tags = Column(String(500), nullable=True, comment="标签（逗号分隔）")
    embedding = Column(Text, nullable=True, comment="向量嵌入（JSON格式，可选）")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])


class Document(Base):
    """文档模型"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False, comment="文件名")
    file_type = Column(String(50), nullable=True, comment="文件类型（pdf, doc, md, html等）")
    file_path = Column(String(1000), nullable=True, comment="文件存储路径")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    title = Column(String(500), nullable=True, comment="文档标题")
    content_hash = Column(String(64), nullable=True, index=True, comment="内容哈希（用于去重）")
    meta_data = Column(JSON, nullable=True, comment="扩展元数据（JSON格式）")
    status = Column(String(20), default="pending", comment="状态（pending, processing, completed, failed）")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """文档分块模型"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    chunk_index = Column(Integer, nullable=False, comment="分块序号")
    content = Column(Text, nullable=False, comment="分块内容")
    meta_data = Column(JSON, nullable=True, comment="分块元数据（页码、章节等，JSON格式）")
    # 向量字段：如果 pgvector 可用则使用 Vector，否则使用 ARRAY
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(768), nullable=True, comment="向量嵌入（pgvector）")
    else:
        embedding = Column(ARRAY(Float), nullable=True, comment="向量嵌入（数组）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    document = relationship("Document", back_populates="chunks")


class DataSourceConfig(Base):
    """数据源配置模型（用于CocoIndex多数据源管理）"""
    __tablename__ = "data_source_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, comment="数据源类型（postgresql, mysql, mongodb, s3, api等）")
    name = Column(String(200), nullable=False, comment="数据源名称")
    config = Column(JSON, nullable=False, comment="连接配置（JSON格式）")
    sync_enabled = Column(Boolean, default=True, comment="是否启用同步")
    sync_frequency = Column(Integer, nullable=True, comment="同步频率（秒）")
    last_sync_at = Column(DateTime(timezone=True), nullable=True, comment="最后同步时间")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建人ID")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User", foreign_keys=[created_by])


class ChatSession(Base):
    """对话会话模型"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    title = Column(String(200), nullable=False, comment="会话标题（可编辑）")
    data_source_id = Column(Integer, ForeignKey("database_configs.id", ondelete="SET NULL"), nullable=True, comment="关联的数据源ID")
    selected_tables = Column(Text, nullable=True, comment="选择的表列表（JSON格式）")
    status = Column(String(20), default="active", comment="状态（active, archived）")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], overlaps="chat_sessions")
    data_source = relationship("DatabaseConfig", foreign_keys=[data_source_id])
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """对话消息模型"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, comment="会话ID")
    role = Column(String(20), nullable=False, comment="角色（user, assistant）")
    content = Column(Text, nullable=False, comment="消息内容")
    sql_statement = Column(Text, nullable=True, comment="生成的SQL（assistant角色）")
    query_result = Column(Text, nullable=True, comment="查询结果（JSON格式）")
    chart_config = Column(Text, nullable=True, comment="图表配置（JSON格式）")
    chart_type = Column(String(50), nullable=True, comment="图表类型")
    error_message = Column(Text, nullable=True, comment="错误信息（如有）")
    tokens_used = Column(Integer, nullable=True, comment="使用的token数")
    response_time = Column(String(20), nullable=True, comment="响应时间（秒）")
    recommended_questions = Column(Text, nullable=True, comment="推荐问题（JSON格式）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")


class Dashboard(Base):
    """仪表板模型"""
    __tablename__ = "dashboards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    name = Column(String(200), nullable=False, comment="仪表板名称")
    description = Column(Text, nullable=True, comment="描述")
    layout_config = Column(Text, nullable=True, comment="布局配置（JSON格式）")
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], overlaps="dashboards")
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardWidget(Base):
    """仪表板组件模型"""
    __tablename__ = "dashboard_widgets"
    
    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, comment="仪表板ID")
    widget_type = Column(String(50), nullable=False, comment="组件类型（chart, table等）")
    title = Column(String(200), nullable=False, comment="组件标题")
    config = Column(Text, nullable=False, comment="组件配置（JSON格式）")
    position_x = Column(Integer, default=0, comment="X坐标")
    position_y = Column(Integer, default=0, comment="Y坐标")
    width = Column(Integer, default=400, comment="宽度")
    height = Column(Integer, default=300, comment="高度")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    dashboard = relationship("Dashboard", back_populates="widgets")


# ==================== 数据连接探查功能相关模型 ====================

class ProbeTask(Base):
    """探查任务模型"""
    __tablename__ = "probe_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    database_config_id = Column(Integer, ForeignKey("database_configs.id", ondelete="CASCADE"), nullable=False, comment="数据源配置ID")
    task_name = Column(String(200), nullable=False, comment="任务名称")
    probe_mode = Column(String(20), default="basic", nullable=False, comment="探查方式：basic/advanced")
    probe_level = Column(String(20), default="database", nullable=False, comment="探查级别：database/table/column")
    scheduling_type = Column(String(20), default="manual", nullable=False, comment="调度类型：manual/cron")
    status = Column(String(20), default="pending", nullable=False, comment="状态：pending/running/completed/failed/stopped")
    progress = Column(Integer, default=0, comment="进度（0-100）")
    start_time = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    end_time = Column(DateTime(timezone=True), nullable=True, comment="结束时间")
    last_probe_time = Column(DateTime(timezone=True), nullable=True, comment="上次探查时间")
    error_message = Column(Text, nullable=True, comment="错误信息")
    is_deleted = Column(Boolean, default=False, comment="是否已删除（软删除）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], overlaps="probe_tasks")
    database_config = relationship("DatabaseConfig", foreign_keys=[database_config_id], overlaps="probe_tasks")
    database_results = relationship("ProbeDatabaseResult", back_populates="task", cascade="all, delete-orphan")
    table_results = relationship("ProbeTableResult", back_populates="task", cascade="all, delete-orphan")
    column_results = relationship("ProbeColumnResult", back_populates="task", cascade="all, delete-orphan")


class ProbeDatabaseResult(Base):
    """库级探查结果模型"""
    __tablename__ = "probe_database_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("probe_tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    database_name = Column(String(200), nullable=False, comment="数据库名")
    db_type = Column(String(50), nullable=False, comment="数据库类型")
    total_size_mb = Column(String(50), nullable=True, comment="总大小（MB）")
    growth_rate = Column(String(50), nullable=True, comment="增长速率")
    table_count = Column(Integer, default=0, comment="表数量")
    view_count = Column(Integer, default=0, comment="视图数量")
    function_count = Column(Integer, default=0, comment="函数数量")
    procedure_count = Column(Integer, default=0, comment="存储过程数量")
    trigger_count = Column(Integer, default=0, comment="触发器数量")
    event_count = Column(Integer, default=0, comment="事件数量（MySQL）")
    sequence_count = Column(Integer, default=0, comment="序列数量（PostgreSQL）")
    top_n_tables = Column(JSON, nullable=True, comment="TOP N大表（JSON格式）")
    cold_tables = Column(JSON, nullable=True, comment="冷表列表（JSON格式）")
    hot_tables = Column(JSON, nullable=True, comment="热表列表（JSON格式）")
    high_risk_accounts = Column(JSON, nullable=True, comment="高危账号列表（JSON格式）")
    permission_summary = Column(JSON, nullable=True, comment="权限摘要（JSON格式）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    task = relationship("ProbeTask", back_populates="database_results")


class ProbeTableResult(Base):
    """表级探查结果模型"""
    __tablename__ = "probe_table_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("probe_tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    database_name = Column(String(200), nullable=False, comment="数据库名")
    table_name = Column(String(200), nullable=False, comment="表名")
    schema_name = Column(String(200), nullable=True, comment="Schema名（PostgreSQL）")
    row_count = Column(Integer, nullable=True, comment="行数")
    table_size_mb = Column(String(50), nullable=True, comment="表大小（MB）")
    index_size_mb = Column(String(50), nullable=True, comment="索引大小（MB）")
    avg_row_length = Column(String(50), nullable=True, comment="平均行长度")
    fragmentation_rate = Column(String(50), nullable=True, comment="碎片率")
    auto_increment_usage = Column(JSON, nullable=True, comment="自增ID使用率（JSON格式）")
    column_count = Column(Integer, default=0, comment="字段数")
    comment = Column(Text, nullable=True, comment="表注释")
    primary_key = Column(JSON, nullable=True, comment="主键（JSON格式）")
    indexes = Column(JSON, nullable=True, comment="索引信息（JSON格式）")
    foreign_keys = Column(JSON, nullable=True, comment="外键信息（JSON格式）")
    constraints = Column(JSON, nullable=True, comment="约束信息（JSON格式）")
    partition_info = Column(JSON, nullable=True, comment="分区信息（JSON格式，如果是分区表）")
    is_cold_table = Column(Boolean, default=False, comment="是否冷表")
    is_hot_table = Column(Boolean, default=False, comment="是否热表")
    last_access_time = Column(DateTime(timezone=True), nullable=True, comment="最后访问时间")
    is_hidden = Column(Boolean, default=False, comment="是否屏蔽")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    task = relationship("ProbeTask", back_populates="table_results")
    column_results = relationship("ProbeColumnResult", back_populates="table_result", cascade="all, delete-orphan")


class ProbeColumnResult(Base):
    """列级探查结果模型"""
    __tablename__ = "probe_column_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("probe_tasks.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    table_result_id = Column(Integer, ForeignKey("probe_table_results.id", ondelete="CASCADE"), nullable=True, comment="表结果ID")
    database_name = Column(String(200), nullable=False, comment="数据库名")
    table_name = Column(String(200), nullable=False, comment="表名")
    column_name = Column(String(200), nullable=False, comment="字段名")
    data_type = Column(String(100), nullable=False, comment="数据类型")
    nullable = Column(Boolean, default=True, comment="是否可空")
    default_value = Column(Text, nullable=True, comment="默认值")
    comment = Column(Text, nullable=True, comment="注释")
    non_null_rate = Column(String(50), nullable=True, comment="非空率")
    distinct_count = Column(Integer, nullable=True, comment="唯一值个数")
    duplicate_rate = Column(String(50), nullable=True, comment="重复率")
    max_length = Column(Integer, nullable=True, comment="最大长度（字符串类型）")
    min_length = Column(Integer, nullable=True, comment="最小长度（字符串类型）")
    avg_length = Column(String(50), nullable=True, comment="平均长度（字符串类型）")
    max_value = Column(String(200), nullable=True, comment="最大值（数值/日期类型）")
    min_value = Column(String(200), nullable=True, comment="最小值（数值/日期类型）")
    top_values = Column(JSON, nullable=True, comment="Top 20高频值（JSON格式）")
    low_frequency_values = Column(JSON, nullable=True, comment="低频长尾值（JSON格式）")
    enum_values = Column(JSON, nullable=True, comment="枚举值清单（JSON格式）")
    zero_count = Column(Integer, nullable=True, comment="零值数量（数值类型）")
    negative_count = Column(Integer, nullable=True, comment="负值数量（数值类型）")
    percentiles = Column(JSON, nullable=True, comment="分位数（P25/P50/P75/P95/P99，JSON格式）")
    date_range = Column(JSON, nullable=True, comment="日期范围（JSON格式，日期类型）")
    missing_rate = Column(String(50), nullable=True, comment="缺失率")
    data_quality_issues = Column(JSON, nullable=True, comment="数据质量问题（JSON格式）")
    sensitive_info = Column(JSON, nullable=True, comment="敏感信息标识（JSON格式）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    task = relationship("ProbeTask", back_populates="column_results")
    table_result = relationship("ProbeTableResult", back_populates="column_results")

