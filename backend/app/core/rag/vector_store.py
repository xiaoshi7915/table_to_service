"""
向量数据库服务
使用 Chroma 实现轻量级向量存储和检索
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None
from loguru import logger
import json


class VectorStore:
    """向量数据库存储服务"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 持久化目录（如果为None，则使用内存模式）
        """
        # 设置持久化目录
        if persist_directory is None:
            # 默认使用项目根目录下的 .chroma 目录
            base_dir = Path(__file__).parent.parent.parent.parent
            persist_directory = str(base_dir / ".chroma")
        
        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 集合名称
        self.collections = {
            "terminologies": "terminologies",  # 术语库
            "sql_examples": "sql_examples",    # SQL示例
            "knowledge": "knowledge",          # 业务知识
        }
        
        # 初始化集合
        self._init_collections()
    
    def _init_collections(self):
        """初始化所有集合"""
        for collection_name in self.collections.values():
            try:
                # 尝试获取集合，如果不存在则创建
                self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
                )
            except Exception as e:
                logger.warning(f"初始化集合 {collection_name} 失败: {e}")
    
    def get_collection(self, collection_name: str):
        """
        获取集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Chroma 集合对象
        """
        if collection_name not in self.collections:
            raise ValueError(f"未知的集合名称: {collection_name}")
        
        return self.client.get_or_create_collection(
            name=self.collections[collection_name],
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_terminology(
        self,
        terminology_id: str,
        business_term: str,
        db_field: str,
        table_name: Optional[str] = None,
        description: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        添加术语到向量数据库
        
        Args:
            terminology_id: 术语ID
            business_term: 业务术语
            db_field: 数据库字段
            table_name: 表名
            description: 描述
            embedding: 嵌入向量（如果为None，需要外部提供）
        """
        collection = self.get_collection("terminologies")
        
        # 构建文档内容
        doc_content = f"{business_term} {description or ''} {db_field} {table_name or ''}".strip()
        
        # 构建元数据
        metadata = {
            "business_term": business_term,
            "db_field": db_field,
            "table_name": table_name or "",
            "description": description or "",
            "type": "terminology"
        }
        
        # 添加文档
        if embedding:
            collection.add(
                documents=[doc_content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[terminology_id]
            )
        else:
            # 如果没有提供嵌入向量，只存储元数据（需要外部生成嵌入）
            collection.add(
                documents=[doc_content],
                metadatas=[metadata],
                ids=[terminology_id]
            )
    
    def add_sql_example(
        self,
        example_id: str,
        question: str,
        sql_statement: str,
        db_type: Optional[str] = None,
        table_name: Optional[str] = None,
        description: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        添加SQL示例到向量数据库
        
        Args:
            example_id: 示例ID
            question: 问题
            sql_statement: SQL语句
            db_type: 数据库类型
            table_name: 表名
            description: 描述
            embedding: 嵌入向量
        """
        collection = self.get_collection("sql_examples")
        
        # 构建文档内容
        doc_content = f"{question} {description or ''} {sql_statement}".strip()
        
        # 构建元数据
        metadata = {
            "question": question,
            "sql_statement": sql_statement,
            "db_type": db_type or "",
            "table_name": table_name or "",
            "description": description or "",
            "type": "sql_example"
        }
        
        # 添加文档
        if embedding:
            collection.add(
                documents=[doc_content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[example_id]
            )
        else:
            collection.add(
                documents=[doc_content],
                metadatas=[metadata],
                ids=[example_id]
            )
    
    def add_knowledge(
        self,
        knowledge_id: str,
        title: str,
        content: str,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        添加业务知识到向量数据库
        
        Args:
            knowledge_id: 知识ID
            title: 标题
            content: 内容
            category: 分类
            tags: 标签
            embedding: 嵌入向量
        """
        collection = self.get_collection("knowledge")
        
        # 构建文档内容
        doc_content = f"{title} {content}".strip()
        
        # 构建元数据
        metadata = {
            "title": title,
            "content": content[:500],  # 限制长度
            "category": category or "",
            "tags": tags or "",
            "type": "knowledge"
        }
        
        # 添加文档
        if embedding:
            collection.add(
                documents=[doc_content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[knowledge_id]
            )
        else:
            collection.add(
                documents=[doc_content],
                metadatas=[metadata],
                ids=[knowledge_id]
            )
    
    def search_terminologies(
        self,
        query_embedding: List[float],
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        检索术语库
        
        Args:
            query_embedding: 查询向量
            limit: 返回数量
            where: 过滤条件
            
        Returns:
            术语列表
        """
        collection = self.get_collection("terminologies")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        terminologies = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results["distances"] else None
                
                terminologies.append({
                    "id": doc_id,
                    "business_term": metadata.get("business_term", ""),
                    "db_field": metadata.get("db_field", ""),
                    "table_name": metadata.get("table_name", ""),
                    "description": metadata.get("description", ""),
                    "similarity": 1 - distance if distance is not None else 0.0
                })
        
        return terminologies
    
    def search_sql_examples(
        self,
        query_embedding: List[float],
        limit: int = 5,
        db_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索SQL示例
        
        Args:
            query_embedding: 查询向量
            limit: 返回数量
            db_type: 数据库类型过滤
            
        Returns:
            SQL示例列表
        """
        collection = self.get_collection("sql_examples")
        
        where = None
        if db_type:
            where = {"db_type": db_type}
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        examples = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results["distances"] else None
                
                examples.append({
                    "id": doc_id,
                    "question": metadata.get("question", ""),
                    "sql_statement": metadata.get("sql_statement", ""),
                    "db_type": metadata.get("db_type", ""),
                    "table_name": metadata.get("table_name", ""),
                    "description": metadata.get("description", ""),
                    "similarity": 1 - distance if distance is not None else 0.0
                })
        
        return examples
    
    def search_knowledge(
        self,
        query_embedding: List[float],
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索业务知识
        
        Args:
            query_embedding: 查询向量
            limit: 返回数量
            category: 分类过滤
            
        Returns:
            知识条目列表
        """
        collection = self.get_collection("knowledge")
        
        where = None
        if category:
            where = {"category": category}
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        knowledge_items = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results["distances"] else None
                
                knowledge_items.append({
                    "id": doc_id,
                    "title": metadata.get("title", ""),
                    "content": metadata.get("content", ""),
                    "category": metadata.get("category", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "similarity": 1 - distance if distance is not None else 0.0
                })
        
        return knowledge_items
    
    def delete_by_id(self, collection_name: str, doc_id: str):
        """
        删除文档
        
        Args:
            collection_name: 集合名称
            doc_id: 文档ID
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=[doc_id])
    
    def update_by_id(
        self,
        collection_name: str,
        doc_id: str,
        document: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        更新文档
        
        Args:
            collection_name: 集合名称
            doc_id: 文档ID
            document: 文档内容
            embedding: 嵌入向量
            metadata: 元数据
        """
        collection = self.get_collection(collection_name)
        
        # 先删除旧文档
        collection.delete(ids=[doc_id])
        
        # 添加新文档
        if document and embedding:
            collection.add(
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata] if metadata else [{}],
                ids=[doc_id]
            )
    
    def reset_collection(self, collection_name: str):
        """
        重置集合（清空所有数据）
        
        Args:
            collection_name: 集合名称
        """
        try:
            collection = self.get_collection(collection_name)
            collection.delete()
            # 重新创建集合
            self._init_collections()
            logger.info(f"集合 {collection_name} 已重置")
        except Exception as e:
            logger.error(f"重置集合 {collection_name} 失败: {e}")


