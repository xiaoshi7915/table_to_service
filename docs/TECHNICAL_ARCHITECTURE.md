# 技术架构文档

## 📋 目录

1. [项目概述](#项目概述)
2. [技术架构](#技术架构)
3. [SQL元数据检索实现](#sql元数据检索实现)
4. [RAG工作流详解](#rag工作流详解)
5. [核心组件说明](#核心组件说明)

---

## 项目概述

**智能问数 + 服务平台** 是一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口，并提供基于大模型+RAG的智能问数功能。

### 核心功能

1. **数据表转接口服务**：将多种数据源的表快速转换为RESTful API接口
2. **智能问数功能**：基于大模型与RAG技术，将"业务人员的一句话"自动转换为"可执行SQL + 可视化图表"

---

## 技术架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  数据源配置   │  │  接口管理     │  │  智能问数     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Nginx 反向代理  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────▼─────────┐ ┌─────▼──────┐ ┌─────────▼─────────┐
│   FastAPI 后端     │ │  MySQL     │ │  PostgreSQL       │
│                    │ │  (元数据)   │ │  (向量存储)        │
│  ┌──────────────┐  │ └────────────┘ └───────────────────┘
│  │  API 路由层   │  │
│  └──────┬───────┘  │
│         │          │
│  ┌──────▼───────┐  │
│  │  业务逻辑层   │  │
│  │              │  │
│  │ ┌──────────┐ │  │
│  │ │ RAG工作流 │ │  │
│  │ └────┬─────┘ │  │
│  │      │       │  │
│  │ ┌────▼─────┐ │  │
│  │ │ Schema服务│ │  │
│  │ └────┬─────┘ │  │
│  │      │       │  │
│  │ ┌────▼─────┐ │  │
│  │ │ 检索服务  │ │  │
│  │ └────┬─────┘ │  │
│  └──────┼───────┘  │
│         │          │
│  ┌──────▼───────┐  │
│  │  数据访问层   │  │
│  └──────────────┘  │
└────────────────────┘
```

### 技术栈

#### 后端技术栈

- **Web框架**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy
- **数据库**: MySQL 8.0+ (元数据存储), PostgreSQL (向量存储，可选)
- **RAG框架**: LangChain + LangGraph
- **向量数据库**: pgvector (PostgreSQL扩展)
- **嵌入模型**: BAAI/bge-base-zh-v1.5 (中文嵌入模型)
- **LLM支持**: OpenAI / 通义千问 / 本地LLM模型
- **缓存**: Redis (可选，支持内存缓存降级)
- **认证**: JWT Token

#### 前端技术栈

- **框架**: Vue 3 + TypeScript
- **UI库**: Element Plus
- **构建工具**: Vite
- **状态管理**: Pinia
- **图表库**: ECharts
- **代码编辑器**: Monaco Editor

---

## SQL元数据检索实现

### 检索流程概览

```
用户提问
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  1. 并行加载Schema和检索上下文                           │
│     ├─ Schema信息加载 (SchemaService)                    │
│     ├─ 术语检索 (HybridRetriever)                        │
│     ├─ SQL示例检索 (HybridRetriever)                     │
│     └─ 业务知识检索 (HybridRetriever)                    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  2. 合并上下文                                            │
│     └─ 去重、排序、限制数量                               │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  3. 构建提示词                                            │
│     ├─ Schema信息格式化                                   │
│     ├─ 上下文信息格式化                                   │
│     ├─ 对话历史格式化                                     │
│     └─ 用户问题                                           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  4. LLM生成SQL                                            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  5. SQL执行和结果处理                                     │
└─────────────────────────────────────────────────────────┘
```

### 1. Schema信息加载

**位置**: `backend/app/core/rag_langchain/schema_service.py`

**实现方式**:

```python
class SchemaService:
    """数据库Schema服务"""
    
    def get_table_schema(
        self,
        table_names: Optional[List[str]] = None,
        include_sample_data: bool = True,
        sample_rows: int = 5
    ) -> Dict[str, Any]:
        """
        获取表结构信息（包含字段、关联关系、样例数据）
        
        实现步骤：
        1. 检查缓存（Redis或内存缓存）
        2. 使用SQLAlchemy Inspector获取表结构
        3. 获取列信息、主键、索引、外键关系
        4. 获取样例数据（可选）
        5. 缓存结果（TTL: 1小时）
        """
```

**关键技术点**:

- **多数据库支持**: 通过 `DatabaseConnectionFactory` 创建不同数据库类型的引擎
- **SQLAlchemy Inspector**: 使用 `inspect(engine)` 获取数据库元数据
- **缓存机制**: 使用Redis或内存缓存，避免重复查询
- **样例数据**: 自动获取表的样例数据，帮助LLM理解数据结构

**支持的数据库类型**:

- MySQL / MariaDB
- PostgreSQL
- SQLite
- SQL Server
- Oracle

### 2. 混合检索器 (HybridRetriever)

**位置**: `backend/app/core/rag_langchain/hybrid_retriever.py`

**实现方式**:

```python
class HybridRetriever:
    """混合检索器（向量检索 + 关键词检索）"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        documents: List[Document],
        vector_weight: float = 0.7,  # 向量检索权重
        keyword_weight: float = 0.3   # 关键词检索权重
    ):
        """
        结合两种检索方式：
        1. 向量检索：基于语义相似度（使用pgvector）
        2. BM25检索：基于关键词匹配
        """
```

**检索流程**:

1. **向量检索** (权重70%):
   - 使用 `bge-base-zh-v1.5` 模型将查询转换为向量
   - 在pgvector中搜索相似向量
   - 返回Top-K个最相似的文档

2. **BM25检索** (权重30%):
   - 使用 `rank_bm25` 库进行关键词匹配
   - 基于TF-IDF算法计算相关性
   - 返回Top-K个最相关的文档

3. **结果合并**:
   - 去重（基于文档内容）
   - 按权重排序
   - 返回Top-N个文档

### 3. 三种知识库检索

#### 3.1 术语检索 (Terminology Retriever)

**数据来源**: `Terminology` 表

**检索内容**:
- 业务术语 (business_term)
- 数据库字段 (db_field)
- 表名 (table_name)
- 描述 (description)

**用途**: 将用户问题中的业务术语映射到数据库字段

**示例**:
```
用户问题: "查询销售额"
术语映射: "销售额" → "sales_amount" (字段名)
```

#### 3.2 SQL示例检索 (SQL Example Retriever)

**数据来源**: `SQLExample` 表

**检索内容**:
- 问题示例 (question)
- SQL语句 (sql_statement)
- 数据库类型 (db_type)
- 表名 (table_name)

**用途**: 提供相似问题的SQL示例，帮助LLM生成正确的SQL

**示例**:
```
用户问题: "查询每个月的销售额"
SQL示例: "SELECT DATE_FORMAT(order_date, '%Y-%m') as month, 
          SUM(amount) as total_sales 
          FROM orders 
          GROUP BY month"
```

#### 3.3 业务知识检索 (Knowledge Retriever)

**数据来源**: `BusinessKnowledge` 表

**检索内容**:
- 标题 (title)
- 内容 (content)
- 分类 (category)

**用途**: 提供业务规则和知识，帮助LLM理解业务逻辑

**示例**:
```
业务知识: "销售额 = 订单金额 - 退款金额"
```

### 4. 向量存储实现

**位置**: `backend/app/core/rag_langchain/vector_store.py`

**技术实现**:

```python
class PGVectorStore:
    """基于pgvector的向量存储"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: Embeddings,
        collection_name: str
    ):
        """
        使用LangChain的PGVector实现向量存储
        
        存储结构：
        - terminologies: 术语向量表
        - sql_examples: SQL示例向量表
        - knowledge: 业务知识向量表
        """
```

**向量化流程**:

1. **文档准备**: 将术语、SQL示例、业务知识转换为LangChain Document对象
2. **向量化**: 使用 `ChineseEmbeddingService` (bge-base-zh-v1.5) 生成768维向量
3. **存储**: 使用pgvector扩展存储到PostgreSQL
4. **索引**: 使用IVFFlat索引加速向量检索

**降级方案**:

- 如果PostgreSQL不可用，自动降级到BM25检索
- 如果向量存储初始化失败，使用空检索器（EmptyRetriever）

---

## RAG工作流详解

### LangGraph工作流

**位置**: `backend/app/core/rag_langchain/rag_workflow.py`

**工作流节点**:

```python
workflow = StateGraph(RAGState)
workflow.add_node("load_schema_and_retrieve", ...)  # 加载Schema和检索
workflow.add_node("merge_contexts", ...)             # 合并上下文
workflow.add_node("build_prompt", ...)               # 构建提示词
workflow.add_node("generate_sql", ...)                # 生成SQL
workflow.add_node("execute_sql", ...)                # 执行SQL
workflow.add_node("handle_error", ...)               # 错误处理
workflow.add_node("generate_chart", ...)             # 生成图表
```

**状态流转**:

```
开始
  │
  ▼
load_schema_and_retrieve (并行加载Schema和检索上下文)
  │
  ▼
merge_contexts (合并上下文)
  │
  ▼
build_prompt (构建提示词)
  │
  ▼
generate_sql (LLM生成SQL)
  │
  ▼
execute_sql (执行SQL)
  │
  ├─ 成功 ──► generate_chart (生成图表) ──► 结束
  │
  └─ 失败 ──► handle_error (错误处理)
              │
              ├─ 重试次数 < max_retries ──► generate_sql (重新生成)
              │
              └─ 重试次数 >= max_retries ──► 结束（返回错误）
```

### 提示词构建

**位置**: `backend/app/core/rag_langchain/rag_workflow.py` - `_build_prompt` 方法

**提示词结构**:

```
你是一个专业的SQL生成助手。请根据以下信息生成SQL查询语句。

## 数据库Schema信息
[表结构、字段、关联关系、样例数据]

## 相关上下文信息
[术语映射、SQL示例、业务知识]

## 对话历史（可能包含参数值）
[最近5条对话消息]

## 用户问题
[当前用户问题]

## 要求
1. 只生成SELECT查询语句
2. 禁止使用临时表
3. 使用参数化查询防止SQL注入
4. 根据问题意图选择合适的聚合函数
5. 合理使用GROUP BY、ORDER BY、LIMIT等子句
6. 生成的SQL要符合数据库语法规范
7. 如果问题中提到了业务术语，请使用对应的数据库字段名
8. 注意表之间的关联关系，使用正确的JOIN语句
```

---

## 核心组件说明

### 1. SchemaService (Schema服务)

**职责**: 从数据库提取表结构、关联关系、样例数据

**关键方法**:
- `get_table_schema()`: 获取表结构信息
- `_get_table_info()`: 获取单个表的详细信息
- `_get_foreign_keys()`: 获取外键关系
- `_get_sample_data()`: 获取样例数据

**性能优化**:
- 缓存机制（Redis或内存缓存）
- 并行查询
- 按需加载（只加载用户选择的表）

### 2. HybridRetriever (混合检索器)

**职责**: 结合向量检索和关键词检索，提供更准确的检索结果

**关键方法**:
- `get_relevant_documents()`: 同步检索
- `aget_relevant_documents()`: 异步检索

**优势**:
- 向量检索：捕获语义相似性
- BM25检索：捕获精确关键词匹配
- 权重融合：结合两种检索方式的优势

### 3. VectorStoreManager (向量存储管理器)

**职责**: 管理多个向量存储集合（术语、SQL示例、业务知识）

**关键方法**:
- `get_store()`: 获取指定集合的向量存储
- `add_documents()`: 添加文档到向量存储
- `search()`: 向量检索

**技术实现**:
- 使用pgvector扩展
- 支持IVFFlat索引
- 自动降级到BM25（如果向量存储不可用）

### 4. RAGWorkflow (RAG工作流)

**职责**: 协调整个RAG流程，从问题到SQL生成

**关键特性**:
- 使用LangGraph实现状态机
- 支持错误重试机制
- 并行执行提升性能
- 详细的思考步骤记录

### 5. SQLExecutor (SQL执行器)

**职责**: 安全执行SQL查询，返回结果

**关键特性**:
- SQL注入防护
- 参数化查询
- 超时控制
- 结果缓存
- 行数限制

---

## 性能优化策略

### 1. 缓存策略

- **Schema缓存**: TTL 1小时，避免重复查询数据库
- **检索结果缓存**: TTL 5分钟，加速相似查询
- **SQL执行结果缓存**: TTL 10分钟，避免重复执行相同SQL

### 2. 并行处理

- **Schema加载和检索并行**: 使用线程池并行执行
- **多种检索并行**: 术语、SQL示例、业务知识并行检索

### 3. 降级方案

- **向量存储不可用**: 降级到BM25检索
- **嵌入模型加载失败**: 降级到传统关键词检索
- **PostgreSQL不可用**: 使用内存缓存代替Redis

### 4. 数据库优化

- **索引优化**: 在术语、SQL示例、业务知识表上创建索引
- **向量索引**: 使用IVFFlat索引加速向量检索
- **连接池**: 使用SQLAlchemy连接池管理数据库连接

---

## 总结

本项目通过以下技术实现了高效的SQL元数据检索：

1. **SchemaService**: 使用SQLAlchemy Inspector从数据库提取元数据
2. **HybridRetriever**: 结合向量检索和BM25检索，提供准确的检索结果
3. **VectorStore**: 使用pgvector存储和检索向量化的知识库
4. **RAGWorkflow**: 使用LangGraph协调整个RAG流程
5. **缓存机制**: 多级缓存提升性能
6. **降级方案**: 确保系统在各种环境下都能正常工作

整个系统设计遵循了**高可用、高性能、易扩展**的原则，能够有效支持智能问数功能。
