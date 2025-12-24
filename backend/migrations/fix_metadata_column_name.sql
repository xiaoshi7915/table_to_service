-- 修复 metadata 字段名冲突
-- SQLAlchemy 中 metadata 是保留字，需要重命名为 meta_data

-- 1. 重命名 documents 表的 metadata 字段
ALTER TABLE documents RENAME COLUMN metadata TO meta_data;

-- 2. 重命名 document_chunks 表的 metadata 字段
ALTER TABLE document_chunks RENAME COLUMN metadata TO meta_data;

-- 3. 更新索引（如果需要）
-- 注意：GIN 索引会自动更新，但为了安全可以重建
DROP INDEX IF EXISTS idx_document_chunks_metadata;
CREATE INDEX IF NOT EXISTS idx_document_chunks_meta_data ON document_chunks USING gin(meta_data jsonb_path_ops);

-- 添加注释
COMMENT ON COLUMN documents.meta_data IS '扩展元数据（JSON格式）';
COMMENT ON COLUMN document_chunks.meta_data IS '分块元数据（页码、章节等，JSON格式）';

