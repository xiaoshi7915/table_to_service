# SQL元数据检索流程详解

## 📊 完整流程图

```mermaid
graph TB
    Start([用户提问]) --> QuestionRewrite[问题改写]
    QuestionRewrite --> LoadSchema[并行加载Schema和检索上下文]
    
    LoadSchema --> SchemaService[SchemaService<br/>加载表结构]
    LoadSchema --> TermRetrieve[术语检索<br/>HybridRetriever]
    LoadSchema --> SQLRetrieve[SQL示例检索<br/>HybridRetriever]
    LoadSchema --> KnowledgeRetrieve[业务知识检索<br/>HybridRetriever]
    
    SchemaService --> SchemaInfo[Schema信息<br/>表结构/字段/关联/样例数据]
    TermRetrieve --> TermDocs[术语文档<br/>业务术语→数据库字段]
    SQLRetrieve --> SQLDocs[SQL示例文档<br/>相似问题的SQL]
    KnowledgeRetrieve --> KnowledgeDocs[业务知识文档<br/>业务规则和知识]
    
    SchemaInfo --> MergeContext[合并上下文]
    TermDocs --> MergeContext
    SQLDocs --> MergeContext
    KnowledgeDocs --> MergeContext
    
    MergeContext --> BuildPrompt[构建提示词]
    BuildPrompt --> GenerateSQL[LLM生成SQL]
    GenerateSQL --> ExecuteSQL[执行SQL]
    
    ExecuteSQL -->|成功| GenerateChart[生成图表]
    ExecuteSQL -->|失败| ErrorHandle[错误处理]
    
    ErrorHandle -->|重试| GenerateSQL
    ErrorHandle -->|达到最大重试次数| ReturnError[返回错误]
    
    GenerateChart --> ReturnSuccess[返回结果]
    ReturnError --> End([结束])
    ReturnSuccess --> End
    
    style Start fill:#e1f5ff
    style End fill:#e1f5ff
    style SchemaService fill:#fff4e1
    style TermRetrieve fill:#fff4e1
    style SQLRetrieve fill:#fff4e1
    style KnowledgeRetrieve fill:#fff4e1
    style GenerateSQL fill:#e8f5e9
    style ExecuteSQL fill:#e8f5e9
```

## 🔍 详细步骤说明

### 步骤1: 问题改写

**位置**: `backend/app/core/rag_langchain/question_rewriter.py`

**功能**: 优化用户问题的表述，提取关键信息

**示例**:
```
原始问题: "查一下销售额"
改写后: "查询销售额数据"
```

### 步骤2: 并行加载Schema和检索上下文

#### 2.1 Schema信息加载

**实现**: `SchemaService.get_table_schema()`

**流程**:
```mermaid
graph LR
    A[检查缓存] -->|命中| B[返回缓存结果]
    A -->|未命中| C[连接数据库]
    C --> D[使用Inspector获取表列表]
    D --> E[获取每个表的结构]
    E --> F[获取列信息/主键/索引]
    F --> G[获取外键关系]
    G --> H[获取样例数据]
    H --> I[缓存结果]
    I --> J[返回Schema信息]
```

**获取的信息**:
- 表名列表
- 每个表的列信息（名称、类型、是否可空、默认值、注释）
- 主键信息
- 索引信息
- 外键关系（表之间的关联）
- 样例数据（前5行）

#### 2.2 术语检索

**实现**: `HybridRetriever.get_relevant_documents()`

**流程**:
```mermaid
graph LR
    A[用户问题] --> B[向量化<br/>bge-base-zh-v1.5]
    A --> C[BM25关键词匹配]
    B --> D[向量检索<br/>pgvector]
    C --> E[BM25检索<br/>rank_bm25]
    D --> F[合并结果<br/>权重: 70% + 30%]
    E --> F
    F --> G[返回Top-K术语]
```

**检索的数据**:
- 业务术语 (business_term)
- 数据库字段 (db_field)
- 表名 (table_name)
- 描述 (description)

#### 2.3 SQL示例检索

**实现**: `HybridRetriever.get_relevant_documents()`

**检索的数据**:
- 问题示例 (question)
- SQL语句 (sql_statement)
- 数据库类型 (db_type)
- 表名 (table_name)

**用途**: 提供相似问题的SQL示例，帮助LLM生成正确的SQL

#### 2.4 业务知识检索

**实现**: `HybridRetriever.get_relevant_documents()`

**检索的数据**:
- 标题 (title)
- 内容 (content)
- 分类 (category)

**用途**: 提供业务规则和知识，帮助LLM理解业务逻辑

### 步骤3: 合并上下文

**实现**: `RAGWorkflow._merge_contexts()`

**流程**:
1. 合并所有检索结果（术语、SQL示例、业务知识）
2. 去重（基于文档内容hash）
3. 限制数量（最多20个文档，避免提示词过长）

### 步骤4: 构建提示词

**实现**: `RAGWorkflow._build_prompt()`

**提示词结构**:
```
## 数据库Schema信息
[表结构、字段、关联关系、样例数据]

## 相关上下文信息
[术语映射、SQL示例、业务知识]

## 对话历史（可能包含参数值）
[最近5条对话消息]

## 用户问题
[当前用户问题]

## 要求
[SQL生成规则和约束]
```

### 步骤5: LLM生成SQL

**实现**: `RAGWorkflow._generate_sql()`

**流程**:
1. 调用LLM API（OpenAI/通义千问/本地模型）
2. 解析LLM返回的SQL
3. 验证SQL语法
4. 提取SQL参数

### 步骤6: 执行SQL

**实现**: `SQLExecutor.execute()`

**流程**:
1. 参数绑定
2. SQL注入检查
3. 执行SQL查询
4. 结果格式化
5. 缓存结果

### 步骤7: 错误处理和重试

**实现**: `RAGWorkflow._handle_error()`

**流程**:
1. 分析错误原因
2. 如果可重试，更新提示词（添加错误信息）
3. 重新生成SQL
4. 最多重试3次

### 步骤8: 生成图表

**实现**: `ChartService.generate_chart_config()`

**流程**:
1. 分析数据特征
2. 根据问题意图选择合适的图表类型
3. 生成ECharts配置

---

## 🎯 关键技术点

### 1. 并行处理

使用 `concurrent.futures.ThreadPoolExecutor` 并行执行：
- Schema加载
- 术语检索
- SQL示例检索
- 业务知识检索

**优势**: 大幅提升性能，减少总耗时

### 2. 混合检索

结合两种检索方式：
- **向量检索** (70%权重): 捕获语义相似性
- **BM25检索** (30%权重): 捕获精确关键词匹配

**优势**: 兼顾语义理解和精确匹配

### 3. 缓存机制

多级缓存：
- **Schema缓存**: TTL 1小时
- **检索结果缓存**: TTL 5分钟
- **SQL执行结果缓存**: TTL 10分钟

**优势**: 避免重复计算，提升响应速度

### 4. 降级方案

确保系统在各种环境下都能工作：
- 向量存储不可用 → BM25检索
- 嵌入模型加载失败 → 关键词检索
- PostgreSQL不可用 → 内存缓存

**优势**: 提高系统可用性和容错性

---

## 📈 性能指标

### 典型响应时间

- **Schema加载**: 100-500ms (缓存命中: <10ms)
- **向量检索**: 50-200ms
- **BM25检索**: 10-50ms
- **LLM生成SQL**: 1-5秒
- **SQL执行**: 100ms-2秒（取决于查询复杂度）

### 优化建议

1. **启用Redis缓存**: 提升缓存性能
2. **使用PostgreSQL + pgvector**: 启用向量检索
3. **配置连接池**: 优化数据库连接管理
4. **使用CDN**: 加速前端资源加载

---

## 🔧 配置说明

### 环境变量

```bash
# 数据库配置
DATABASE_URL=mysql://user:password@localhost/dbname
LOCAL_DATABASE_URL=postgresql://user:password@localhost/dbname

# Redis配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM配置
OPENAI_API_KEY=your_key
DASHSCOPE_API_KEY=your_key

# Hugging Face镜像（用于下载模型）
HF_ENDPOINT=https://hf-mirror.com
```

### 数据库表结构

#### Terminology (术语表)
```sql
CREATE TABLE terminologies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    business_term VARCHAR(255),  -- 业务术语
    db_field VARCHAR(255),       -- 数据库字段
    table_name VARCHAR(255),      -- 表名
    description TEXT,            -- 描述
    created_at TIMESTAMP
);
```

#### SQLExample (SQL示例表)
```sql
CREATE TABLE sql_examples (
    id INT PRIMARY KEY AUTO_INCREMENT,
    question TEXT,              -- 问题示例
    sql_statement TEXT,          -- SQL语句
    db_type VARCHAR(50),        -- 数据库类型
    table_name VARCHAR(255),    -- 表名
    description TEXT,           -- 描述
    created_at TIMESTAMP
);
```

#### BusinessKnowledge (业务知识表)
```sql
CREATE TABLE business_knowledge (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255),        -- 标题
    content TEXT,               -- 内容
    category VARCHAR(100),      -- 分类
    created_at TIMESTAMP
);
```

---

## 📚 相关文档

- [技术架构文档](./TECHNICAL_ARCHITECTURE.md)
- [用户使用手册](./USER_MANUAL.md)
- [API文档](http://121.36.205.70:8300/docs)
