# 后端RAG服务重构规划

## 📋 概述

参考 SQLBot 项目架构，使用 LangChain + LangGraph + pgvector 重构 RAG 服务，实现更强大的检索增强生成能力。

## 🎯 核心目标

1. **使用 LangChain 技术栈**：统一使用 LangChain 生态
2. **中文嵌入模型**：使用 text2vec-base-chinese
3. **pgvector 存储**：使用 PostgreSQL + pgvector 存储向量
4. **混合检索**：语义检索 + 关键词检索
5. **文本分块**：知识库上传时自动分块
6. **多步骤RAG**：使用 LangGraph 实现查询分解-检索-生成流程

## 🏗️ 架构设计

### 1. 数据存储层

```
PostgreSQL (metadata)
├── 术语库表 (terminologies)
├── SQL示例表 (sql_examples)
├── 业务知识表 (business_knowledge)
├── 知识块表 (knowledge_chunks)  # 新增：存储分块后的知识
└── 向量表 (使用 pgvector extension)
    ├── terminology_embeddings
    ├── sql_example_embeddings
    └── knowledge_chunk_embeddings
```

### 2. 核心服务层

```
RAG服务架构
├── EmbeddingService (嵌入服务)
│   └── 使用 text2vec-base-chinese
├── VectorStore (向量存储)
│   └── 使用 pgvector + LangChain VectorStore
├── TextSplitter (文本分块)
│   └── 使用 LangChain RecursiveCharacterTextSplitter
├── Retriever (检索器)
│   ├── VectorRetriever (向量检索)
│   ├── KeywordRetriever (关键词检索)
│   └── HybridRetriever (混合检索)
├── RAGChain (RAG链)
│   └── 使用 LangChain RAG链
└── RAGGraph (RAG工作流)
    └── 使用 LangGraph 实现多步骤流程
```

### 3. 多步骤RAG流程（LangGraph）

```
用户问题
  ↓
[步骤1: 查询理解]
  - 分析问题意图
  - 提取关键信息
  - 确定检索策略
  ↓
[步骤2: 查询分解]
  - 将复杂问题分解为子问题
  - 确定每个子问题的检索范围
  ↓
[步骤3: 并行检索]
  - 术语库检索（向量+关键词）
  - SQL示例检索（向量+关键词）
  - 业务知识检索（向量+关键词）
  - 数据库Schema检索
  ↓
[步骤4: 结果融合]
  - 合并检索结果
  - 去重和排序
  - 选择最相关的上下文
  ↓
[步骤5: 提示词构建]
  - 构建完整提示词
  - 注入上下文信息
  ↓
[步骤6: SQL生成]
  - 调用LLM生成SQL
  - 验证和优化SQL
  ↓
[步骤7: 结果返回]
  - 返回SQL和说明
```

## 📦 依赖包更新

### 核心依赖

```txt
# LangChain生态
langchain>=0.3,<0.4
langchain-core>=0.3,<0.4
langchain-openai>=0.3,<0.4
langchain-community>=0.3,<0.4
langchain-huggingface>=0.2.0
langgraph>=0.3,<0.4

# 向量存储
pgvector>=0.4.1
psycopg[binary]>=3.1.13,<4.0.0

# 嵌入模型
sentence-transformers>=4.0.2

# 数据库
sqlmodel>=0.0.21,<1.0.0
alembic>=1.12.1,<2.0.0

# 其他
tenacity>=8.2.3,<9.0.0
pydantic>=2.0
pydantic-settings>=2.2.1
```

## 🔧 实现模块

### 1. 数据库模型扩展

**新增表：knowledge_chunks（知识块表）**

```python
class KnowledgeChunk(Base):
    """知识块模型"""
    __tablename__ = "knowledge_chunks"
    
    id = Column(Integer, primary_key=True)
    knowledge_id = Column(Integer, ForeignKey("business_knowledge.id"))
    chunk_index = Column(Integer)  # 块索引
    content = Column(Text)  # 块内容
    metadata = Column(JSON)  # 元数据（包含位置、长度等）
    embedding_id = Column(Integer)  # 关联的向量ID
    created_at = Column(DateTime)
```

**pgvector扩展**

```sql
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建向量表
CREATE TABLE terminology_embeddings (
    id SERIAL PRIMARY KEY,
    terminology_id INTEGER REFERENCES terminologies(id),
    embedding vector(768),  -- text2vec-base-chinese维度
    metadata JSONB
);

CREATE INDEX ON terminology_embeddings 
USING ivfflat (embedding vector_cosine_ops);
```

### 2. 嵌入服务（EmbeddingService）

```python
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.embeddings.base import Embeddings

class ChineseEmbeddingService:
    """中文嵌入服务"""
    
    def __init__(self):
        self.model_name = "text2vec-base-chinese"
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs={'device': 'cpu'}
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """生成查询向量"""
        return self.embeddings.embed_query(text)
```

### 3. 文本分块服务（TextSplitter）

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

class KnowledgeTextSplitter:
    """知识库文本分块器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or ["\n\n", "\n", "。", "，", " ", ""],
            length_function=len,
            is_separator_regex=False
        )
    
    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        return self.splitter.split_text(text)
    
    def split_documents(self, documents: List[Dict]) -> List[Dict]:
        """分割文档（保留元数据）"""
        chunks = []
        for doc in documents:
            text_chunks = self.split_text(doc["content"])
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    "content": chunk,
                    "metadata": {
                        **doc.get("metadata", {}),
                        "chunk_index": i,
                        "source": doc.get("id"),
                        "title": doc.get("title", "")
                    }
                })
        return chunks
```

### 4. 向量存储服务（VectorStore）

```python
from langchain.vectorstores import PGVector
from langchain.schema import Document

class PGVectorStore:
    """基于pgvector的向量存储"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: ChineseEmbeddingService,
        collection_name: str
    ):
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_store = PGVector(
            connection_string=connection_string,
            embedding_function=embedding_service.embeddings,
            collection_name=collection_name
        )
    
    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None
    ):
        """添加文档"""
        return self.vector_store.add_documents(
            documents=documents,
            ids=ids
        )
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """相似度搜索"""
        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Tuple[Document, float]]:
        """相似度搜索（带分数）"""
        return self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter
        )
```

### 5. 混合检索器（HybridRetriever）

```python
from langchain.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

class HybridRetriever:
    """混合检索器（向量+关键词）"""
    
    def __init__(
        self,
        vector_store: PGVectorStore,
        documents: List[Document],
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        # 向量检索器
        self.vector_retriever = vector_store.as_retriever(
            search_kwargs={"k": 10}
        )
        
        # 关键词检索器（BM25）
        self.keyword_retriever = BM25Retriever.from_documents(documents)
        self.keyword_retriever.k = 10
        
        # 混合检索器
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.vector_retriever, self.keyword_retriever],
            weights=[vector_weight, keyword_weight]
        )
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """检索相关文档"""
        return self.ensemble_retriever.get_relevant_documents(query)
```

### 6. RAG链（RAGChain）

```python
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain

class SQLRAGChain:
    """SQL生成RAG链"""
    
    def __init__(
        self,
        llm: BaseChatModel,
        retriever: HybridRetriever,
        prompt_template: Optional[str] = None
    ):
        self.llm = llm
        self.retriever = retriever
        
        # 默认提示词模板
        self.prompt_template = prompt_template or """
根据以下上下文信息生成SQL查询语句。

上下文信息：
{context}

用户问题：{question}

要求：
1. 只生成SELECT查询语句
2. 使用参数化查询防止SQL注入
3. 符合{db_type}语法规范
4. 如果问题中提到了业务术语，请使用对应的数据库字段名

SQL语句："""
        
        self.prompt = PromptTemplate(
            template=self.prompt_template,
            input_variables=["context", "question", "db_type"]
        )
        
        # 创建RAG链
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": self.prompt},
            return_source_documents=True
        )
    
    def generate_sql(
        self,
        question: str,
        db_type: str = "mysql"
    ) -> Dict[str, Any]:
        """生成SQL"""
        result = self.qa_chain.invoke({
            "query": question,
            "db_type": db_type
        })
        
        return {
            "sql": result["result"],
            "source_documents": result.get("source_documents", [])
        }
```

### 7. RAG工作流（LangGraph）

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class RAGState(TypedDict):
    """RAG状态"""
    question: str
    decomposed_queries: List[str]
    retrieved_contexts: Dict[str, List[Document]]
    merged_context: List[Document]
    prompt: str
    sql: str
    explanation: str

class RAGWorkflow:
    """RAG工作流（使用LangGraph）"""
    
    def __init__(
        self,
        llm: BaseChatModel,
        terminology_retriever: HybridRetriever,
        sql_example_retriever: HybridRetriever,
        knowledge_retriever: HybridRetriever,
        schema_loader: SchemaLoader
    ):
        self.llm = llm
        self.terminology_retriever = terminology_retriever
        self.sql_example_retriever = sql_example_retriever
        self.knowledge_retriever = knowledge_retriever
        self.schema_loader = schema_loader
        
        # 构建工作流图
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(RAGState)
        
        # 添加节点
        workflow.add_node("understand_query", self._understand_query)
        workflow.add_node("decompose_query", self._decompose_query)
        workflow.add_node("retrieve_terminologies", self._retrieve_terminologies)
        workflow.add_node("retrieve_sql_examples", self._retrieve_sql_examples)
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge)
        workflow.add_node("merge_contexts", self._merge_contexts)
        workflow.add_node("build_prompt", self._build_prompt)
        workflow.add_node("generate_sql", self._generate_sql)
        
        # 设置入口
        workflow.set_entry_point("understand_query")
        
        # 添加边
        workflow.add_edge("understand_query", "decompose_query")
        workflow.add_edge("decompose_query", "retrieve_terminologies")
        workflow.add_edge("retrieve_terminologies", "retrieve_sql_examples")
        workflow.add_edge("retrieve_sql_examples", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "merge_contexts")
        workflow.add_edge("merge_contexts", "build_prompt")
        workflow.add_edge("build_prompt", "generate_sql")
        workflow.add_edge("generate_sql", END)
        
        return workflow.compile()
    
    def _understand_query(self, state: RAGState) -> RAGState:
        """理解查询"""
        # 使用LLM分析问题意图
        # ...
        return state
    
    def _decompose_query(self, state: RAGState) -> RAGState:
        """分解查询"""
        # 将复杂问题分解为子问题
        # ...
        return state
    
    def _retrieve_terminologies(self, state: RAGState) -> RAGState:
        """检索术语"""
        docs = self.terminology_retriever.get_relevant_documents(
            state["question"]
        )
        state["retrieved_contexts"]["terminologies"] = docs
        return state
    
    def _retrieve_sql_examples(self, state: RAGState) -> RAGState:
        """检索SQL示例"""
        docs = self.sql_example_retriever.get_relevant_documents(
            state["question"]
        )
        state["retrieved_contexts"]["sql_examples"] = docs
        return state
    
    def _retrieve_knowledge(self, state: RAGState) -> RAGState:
        """检索业务知识"""
        docs = self.knowledge_retriever.get_relevant_documents(
            state["question"]
        )
        state["retrieved_contexts"]["knowledge"] = docs
        return state
    
    def _merge_contexts(self, state: RAGState) -> RAGState:
        """合并上下文"""
        # 合并所有检索结果，去重和排序
        # ...
        return state
    
    def _build_prompt(self, state: RAGState) -> RAGState:
        """构建提示词"""
        # 构建完整提示词
        # ...
        return state
    
    def _generate_sql(self, state: RAGState) -> RAGState:
        """生成SQL"""
        # 调用LLM生成SQL
        # ...
        return state
    
    def run(self, question: str, db_type: str = "mysql") -> Dict[str, Any]:
        """运行工作流"""
        initial_state = RAGState(
            question=question,
            decomposed_queries=[],
            retrieved_contexts={},
            merged_context=[],
            prompt="",
            sql="",
            explanation=""
        )
        
        result = self.workflow.invoke(initial_state)
        return result
```

## 📝 实现步骤

### 阶段1：基础设施（2-3天）✅ 已完成

1. ✅ 更新依赖包（requirements.txt）
2. ✅ 创建pgvector扩展脚本（init_pgvector.py）
3. ✅ 创建向量表结构
4. ✅ 实现中文嵌入服务（embedding_service.py）
5. ✅ 实现文本分块服务（text_splitter.py）

### 阶段2：向量存储（2-3天）✅ 已完成

1. ✅ 实现PGVectorStore（vector_store.py）
2. ✅ 实现VectorStoreManager
3. ⏳ 实现知识库导入（含分块）- 待实现
4. ⏳ 实现向量索引优化 - 待实现

### 阶段3：检索器（2-3天）✅ 已完成

1. ✅ 实现向量检索器（集成在PGVectorStore中）
2. ✅ 实现关键词检索器（BM25）- 集成在HybridRetriever中
3. ✅ 实现混合检索器（hybrid_retriever.py）

### 阶段4：RAG链（2-3天）✅ 已完成

1. ✅ 实现基础RAG链（rag_chain.py）
2. ⏳ 实现提示词模板管理 - 待实现
3. ⏳ 集成到SQL生成服务 - 待实现

### 阶段5：LangGraph工作流（3-4天）⏳ 待实现

1. ⏳ 设计状态图
2. ⏳ 实现各节点逻辑
3. ⏳ 实现工作流编排
4. ⏳ 测试和优化

### 阶段6：集成和测试（2-3天）⏳ 待实现

1. ⏳ 集成到对话API
2. ⏳ 性能测试
3. ⏳ 准确性测试
4. ⏳ 文档更新

## 📦 已创建的文件

### 核心模块
```
backend/app/core/rag_langchain/
├── __init__.py                    # 模块初始化
├── embedding_service.py          # 中文嵌入服务（text2vec-base-chinese）
├── text_splitter.py              # 中文文本分块器
├── vector_store.py               # pgvector向量存储
├── hybrid_retriever.py           # 混合检索器
└── rag_chain.py                  # RAG链
```

### 初始化脚本
```
backend/scripts/
└── init_pgvector.py              # pgvector扩展初始化脚本
```

## 🔧 下一步工作

### 1. 实现LangGraph工作流

创建 `rag_workflow.py`，实现多步骤RAG流程：
- 查询理解
- 查询分解
- 并行检索
- 结果融合
- 提示词构建
- SQL生成

### 2. 实现知识库导入服务

创建 `knowledge_importer.py`，实现：
- 文本分块
- 生成嵌入向量
- 导入到pgvector
- 增量更新

### 3. 更新对话API

修改 `chat.py`，集成新的RAG服务：
- 使用LangChain RAG链
- 使用混合检索
- 使用LangGraph工作流

### 4. 数据库迁移

创建Alembic迁移脚本：
- 添加knowledge_chunks表
- 添加pgvector扩展
- 创建向量表

## 🔄 数据迁移

### 从Chroma迁移到pgvector

1. 导出Chroma数据
2. 转换格式
3. 导入到pgvector
4. 验证数据完整性

## 📊 性能优化

1. **向量索引**：使用IVFFlat索引加速检索
2. **批量处理**：批量生成嵌入向量
3. **缓存机制**：缓存常用查询结果
4. **异步处理**：使用异步IO提升并发性能

## 🎯 关键特性

1. **中文优化**：使用text2vec-base-chinese，针对中文优化
2. **混合检索**：结合语义和关键词，提升检索准确性
3. **智能分块**：根据中文特点优化分块策略
4. **多步骤RAG**：使用LangGraph实现复杂流程编排
5. **可扩展性**：模块化设计，易于扩展

---

**规划日期**：2025-12-19  
**参考项目**：SQLBot  
**技术栈**：LangChain + LangGraph + pgvector + text2vec-base-chinese

