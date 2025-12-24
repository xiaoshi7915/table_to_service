-- CocoIndex 相关表结构迁移脚本
-- 用于文档管理和数据源配置

-- 1. 文档表
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_path VARCHAR(1000),
    file_size INTEGER,
    title VARCHAR(500),
    content_hash VARCHAR(64),
    meta_data JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by);
CREATE INDEX IF NOT EXISTS idx_documents_is_deleted ON documents(is_deleted);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);

-- 2. 文档分块表（带向量）
-- 注意：需要先确保 pgvector 扩展已安装
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    meta_data JSONB,
    embedding vector(768),  -- pgvector，768维向量
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_index ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_document_chunks_meta_data ON document_chunks USING gin(meta_data jsonb_path_ops);

-- 创建向量索引（如果 pgvector 可用）
-- 注意：ivfflat 索引需要先有数据才能创建，这里先注释掉
-- CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 3. 数据源配置表
CREATE TABLE IF NOT EXISTS data_source_configs (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    config JSONB NOT NULL,
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_frequency INTEGER,  -- 同步频率（秒）
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_data_source_configs_source_type ON data_source_configs(source_type);
CREATE INDEX IF NOT EXISTS idx_data_source_configs_sync_enabled ON data_source_configs(sync_enabled);
CREATE INDEX IF NOT EXISTS idx_data_source_configs_is_deleted ON data_source_configs(is_deleted);
CREATE UNIQUE INDEX IF NOT EXISTS idx_data_source_configs_name ON data_source_configs(name) WHERE is_deleted = FALSE;

-- 添加注释
COMMENT ON TABLE documents IS '文档表，存储上传的文档信息';
COMMENT ON TABLE document_chunks IS '文档分块表，存储文档的分块内容和向量';
COMMENT ON TABLE data_source_configs IS '数据源配置表，用于CocoIndex多数据源管理';

COMMENT ON COLUMN documents.content_hash IS '内容哈希值，用于去重';
COMMENT ON COLUMN documents.status IS '文档状态：pending（待处理）、processing（处理中）、completed（已完成）、failed（失败）';
COMMENT ON COLUMN documents.meta_data IS '扩展元数据（JSON格式）';
COMMENT ON COLUMN document_chunks.embedding IS '向量嵌入（pgvector），768维';
COMMENT ON COLUMN document_chunks.meta_data IS '分块元数据（页码、章节等，JSON格式）';
COMMENT ON COLUMN data_source_configs.source_type IS '数据源类型：postgresql、mysql、mongodb、s3、api等';
COMMENT ON COLUMN data_source_configs.config IS '连接配置（JSON格式）';

