# CocoIndex 架构集成实施状态

## 已完成的工作

### 阶段1：环境准备和依赖安装 ✅
- ✅ 添加 CocoIndex 和相关依赖到 `requirements.txt`
- ✅ 创建 CocoIndex 配置模块 (`backend/app/core/cocoindex/config.py`)
- ✅ 更新主配置文件添加 CocoIndex 相关配置

### 阶段2：文档处理系统 ✅
- ✅ 创建文档数据模型 (`Document`, `DocumentChunk`, `DataSourceConfig`)
- ✅ 实现文档解析器（PDF、DOC、MD、HTML、TXT）
- ✅ 实现文档分块器（基于语义和长度）
- ✅ 实现元数据提取器（支持LLM辅助提取）
- ✅ 创建文档上传API (`backend/app/api/v1/documents.py`)
- ✅ 创建数据库迁移脚本 (`backend/migrations/add_cocoindex_tables.sql`)

### 阶段3：CocoIndex Sources ✅
- ✅ 创建基础Source接口 (`BaseSource`)
- ✅ 实现 PostgreSQL Source（术语库、SQL示例、提示词）
- ✅ 实现 File Source（文档上传）
- ✅ 实现 Database Schema Source（关系型数据库）
- ✅ 创建数据源注册表 (`SourceRegistry`)

### 阶段4：CocoIndex Indexes 和 Pipelines ✅
- ✅ 创建 PostgreSQL Index 配置 (`PostgresIndex`)
- ✅ 实现 Transformers（Knowledge、Document、Schema）
- ✅ 创建 Pipelines（Knowledge、Document、Schema）

### 阶段5：同步服务 ✅
- ✅ 创建同步服务基础结构 (`SyncService`)
- ✅ 实现同步状态管理

### 阶段6：混合召回 ✅
- ✅ 创建 CocoIndex 检索器 (`CocoIndexRetriever`)
- ✅ 实现混合召回策略（向量+关键词+RRF融合）
- ✅ 创建兼容层适配器（集成到RAG工作流）

### 阶段7：API 和管理界面 ✅
- ✅ 创建文档管理API (`/api/v1/documents`)
- ✅ 创建数据源管理API (`/api/v1/data-sources`)
- ✅ 创建 CocoIndex 管理API (`/api/v1/cocoindex`)
- ✅ 更新 RAG 工作流支持 CocoIndex 检索器

## 待完善的工作

### 1. CocoIndex 库集成 ✅
- ✅ 完善 Pipeline 中的索引实现（支持降级到直接数据库插入）
- ✅ 完善检索器实现（支持降级到直接数据库查询）
- ✅ 创建索引管理器（统一管理索引创建）
- ⚠️ 需要实际安装和测试 `cocoindex` Python 包（待实际测试）
- ⚠️ 根据实际的 CocoIndex API 调整代码实现（框架已就绪）

### 2. 更多数据源类型 ✅
- ✅ MongoDB Source（使用 Change Streams）
- ✅ S3/Azure Blob/Google Drive Sources
- ✅ REST/GraphQL API Source

### 3. CDC 实现 ✅
- ✅ PostgreSQL CDC 监听器（轮询方式，可升级为 logical replication）
- ✅ 文件系统事件监听（使用 watchdog）
- ✅ 文档处理队列（异步处理）
- ✅ 增量更新引擎
- ✅ 定时同步任务（使用 APScheduler）

### 4. 前端界面 ✅
- ✅ 文档管理界面 (`DocumentManagement.vue`)
- ✅ 数据源配置界面 (`DataSourceManagement.vue`)
- ✅ CocoIndex 状态监控界面 (`CocoIndexConfig.vue`)

### 5. 数据迁移 ✅
- ✅ 创建数据迁移脚本 (`backend/scripts/migrate_to_cocoindex.py`)
- ⚠️ 测试迁移过程（需要实际运行测试）

### 6. 测试和优化 ✅
- ✅ 创建批量处理器（支持批量处理和重试）
- ✅ 创建健康检查器（检查各组件状态）
- ✅ 创建向量嵌入辅助工具（批量生成向量）
- ✅ 完善错误处理和降级机制
- ⚠️ 单元测试（待编写）
- ⚠️ 集成测试（待编写）
- ⚠️ 性能测试和优化（待实际测试）

## 使用说明

### 1. 安装依赖
```bash
cd /opt/table_to_service/backend
pip install -r requirements.txt
```

### 2. 运行数据库迁移
```bash
# 连接到PostgreSQL数据库，执行迁移脚本
psql -U your_user -d your_database -f migrations/add_cocoindex_tables.sql
```

### 3. 配置环境变量
在 `.env` 文件中添加：
```env
# CocoIndex 配置
USE_COCOINDEX_RETRIEVER=false  # 设置为 true 启用 CocoIndex 检索器
DOCUMENT_STORAGE_PATH=/path/to/storage/documents
EMBEDDING_MODEL=bge-base-zh-v1.5
EMBEDDING_DIMENSION=768
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### 4. 启动服务
```bash
cd /opt/table_to_service/backend
uvicorn app.main:app --host 0.0.0.0 --port 5001
```

## API 端点

### 文档管理
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents` - 获取文档列表
- `GET /api/v1/documents/{id}` - 获取文档详情
- `DELETE /api/v1/documents/{id}` - 删除文档

### 数据源管理
- `POST /api/v1/data-sources` - 创建数据源配置
- `GET /api/v1/data-sources` - 获取数据源列表
- `GET /api/v1/data-sources/{id}` - 获取数据源详情
- `PUT /api/v1/data-sources/{id}` - 更新数据源配置
- `DELETE /api/v1/data-sources/{id}` - 删除数据源配置
- `POST /api/v1/data-sources/{id}/sync` - 手动触发同步
- `GET /api/v1/data-sources/{id}/sync-status` - 获取同步状态

### CocoIndex 管理
- `GET /api/v1/cocoindex/status` - 获取索引状态统计
- `GET /api/v1/cocoindex/sync-status` - 获取所有同步状态
- `POST /api/v1/cocoindex/sync-all` - 同步所有启用的数据源

## 注意事项

1. **CocoIndex 库**：当前代码中使用了 CocoIndex，但需要实际安装和测试。如果库不可用，系统会降级到现有检索方式。

2. **向量索引**：文档分块表的向量索引（ivfflat）需要在有数据后才能创建。可以在数据导入后手动创建：
   ```sql
   CREATE INDEX idx_document_chunks_embedding ON document_chunks 
   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
   ```

3. **异步处理**：文档上传后会在后台异步处理（解析、分块、向量化）。可以通过文档状态API查询处理进度。

4. **向后兼容**：当前实现保持了向后兼容性，默认使用现有检索方式。可以通过配置 `USE_COCOINDEX_RETRIEVER=true` 启用 CocoIndex 检索器。

## 下一步工作

1. 安装和测试 CocoIndex 库
2. 完善 CDC 实现
3. 实现更多数据源类型
4. 创建前端管理界面
5. 进行端到端测试
6. 性能优化

