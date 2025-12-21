-- 添加软删除字段的迁移脚本
-- 为所有需要软删除的表添加 is_deleted 字段

-- 数据库配置表
ALTER TABLE database_configs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 接口配置表
ALTER TABLE interface_configs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 接口参数表
ALTER TABLE interface_parameters ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 接口请求头表
ALTER TABLE interface_headers ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- AI模型配置表
ALTER TABLE ai_model_configs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 术语库表
ALTER TABLE terminologies ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- SQL示例表
ALTER TABLE sql_examples ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 自定义提示词表
ALTER TABLE custom_prompts ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 业务知识库表
ALTER TABLE business_knowledge ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 对话会话表
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 仪表板表
ALTER TABLE dashboards ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 仪表板组件表
ALTER TABLE dashboard_widgets ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 探查任务表
ALTER TABLE probe_tasks ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除（软删除）';

-- 为所有 is_deleted 字段创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_database_configs_is_deleted ON database_configs(is_deleted);
CREATE INDEX IF NOT EXISTS idx_interface_configs_is_deleted ON interface_configs(is_deleted);
CREATE INDEX IF NOT EXISTS idx_interface_parameters_is_deleted ON interface_parameters(is_deleted);
CREATE INDEX IF NOT EXISTS idx_interface_headers_is_deleted ON interface_headers(is_deleted);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_is_deleted ON ai_model_configs(is_deleted);
CREATE INDEX IF NOT EXISTS idx_terminologies_is_deleted ON terminologies(is_deleted);
CREATE INDEX IF NOT EXISTS idx_sql_examples_is_deleted ON sql_examples(is_deleted);
CREATE INDEX IF NOT EXISTS idx_custom_prompts_is_deleted ON custom_prompts(is_deleted);
CREATE INDEX IF NOT EXISTS idx_business_knowledge_is_deleted ON business_knowledge(is_deleted);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_deleted ON chat_sessions(is_deleted);
CREATE INDEX IF NOT EXISTS idx_dashboards_is_deleted ON dashboards(is_deleted);
CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_is_deleted ON dashboard_widgets(is_deleted);
CREATE INDEX IF NOT EXISTS idx_probe_tasks_is_deleted ON probe_tasks(is_deleted);

