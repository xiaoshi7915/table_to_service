"""
知识库检索服务
使用向量数据库实现语义检索
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from loguru import logger

from app.models import (
    Terminology, SQLExample, CustomPrompt, BusinessKnowledge
)
from .vector_store import VectorStore
from .embedding_service import EmbeddingService


class KnowledgeRetriever:
    """知识库检索器（基于向量数据库）"""
    
    def __init__(
        self,
        db: Session,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        初始化检索器
        
        Args:
            db: 数据库会话
            vector_store: 向量数据库（如果为None，则使用传统检索）
            embedding_service: 嵌入服务（如果为None，则使用传统检索）
        """
        self.db = db
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.use_vector_search = vector_store is not None and embedding_service is not None
    
    def retrieve_terminologies(self, question: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索术语库
        
        优先使用向量检索，如果不可用则降级到传统检索
        
        Args:
            question: 用户问题
            limit: 返回的最大数量
            
        Returns:
            术语列表，每个术语包含：business_term, db_field, table_name, category, description
        """
        try:
            # 使用向量检索
            if self.use_vector_search:
                try:
                    # 生成查询向量
                    query_embedding = self.embedding_service.generate_embedding(question)
                    
                    # 向量检索
                    results = self.vector_store.search_terminologies(
                        query_embedding=query_embedding,
                        limit=limit
                    )
                    
                    logger.info(f"向量检索到 {len(results)} 个术语")
                    return results
                except Exception as e:
                    logger.warning(f"向量检索失败，降级到传统检索: {e}")
            
            # 传统检索（降级方案）
            question_lower = question.lower()
            
            # 检索匹配的术语
            exact_matches = self.db.query(Terminology).filter(
                Terminology.business_term.ilike(f"%{question}%")
            ).limit(limit).all()
            
            fuzzy_matches = self.db.query(Terminology).filter(
                or_(
                    Terminology.business_term.ilike(f"%{question}%"),
                    Terminology.description.ilike(f"%{question}%")
                )
            ).limit(limit).all()
            
            # 合并结果并去重
            seen = set()
            results = []
            
            for term in exact_matches + fuzzy_matches:
                if term.id not in seen:
                    seen.add(term.id)
                    results.append({
                        "business_term": term.business_term,
                        "db_field": term.db_field,
                        "table_name": term.table_name,
                        "category": term.category,
                        "description": term.description,
                        "similarity": 0.5  # 传统检索没有相似度，给默认值
                    })
            
            logger.info(f"传统检索到 {len(results)} 个术语")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"检索术语库失败: {e}", exc_info=True)
            return []
    
    def retrieve_sql_examples(
        self, 
        question: str, 
        db_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索SQL示例
        
        优先使用向量检索，如果不可用则降级到传统检索
        
        Args:
            question: 用户问题
            db_type: 数据库类型（可选，用于筛选）
            limit: 返回的最大数量
            
        Returns:
            SQL示例列表
        """
        try:
            # 使用向量检索
            if self.use_vector_search:
                try:
                    # 生成查询向量
                    query_embedding = self.embedding_service.generate_embedding(question)
                    
                    # 向量检索
                    results = self.vector_store.search_sql_examples(
                        query_embedding=query_embedding,
                        limit=limit,
                        db_type=db_type
                    )
                    
                    logger.info(f"向量检索到 {len(results)} 个SQL示例")
                    return results
                except Exception as e:
                    logger.warning(f"向量检索失败，降级到传统检索: {e}")
            
            # 传统检索（降级方案）
            query = self.db.query(SQLExample)
            
            if db_type:
                query = query.filter(SQLExample.db_type == db_type)
            
            examples = query.filter(
                or_(
                    SQLExample.question.ilike(f"%{question}%"),
                    SQLExample.title.ilike(f"%{question}%"),
                    SQLExample.description.ilike(f"%{question}%")
                )
            ).limit(limit * 2).all()
            
            # 按相似度排序
            results = []
            for example in examples:
                similarity = self._calculate_similarity(
                    question.lower(),
                    f"{example.question} {example.title}".lower()
                )
                results.append({
                    "id": example.id,
                    "title": example.title,
                    "question": example.question,
                    "sql_statement": example.sql_statement,
                    "db_type": example.db_type,
                    "table_name": example.table_name,
                    "chart_type": example.chart_type,
                    "description": example.description,
                    "similarity": similarity
                })
            
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"传统检索到 {len(results)} 个SQL示例")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"检索SQL示例失败: {e}", exc_info=True)
            return []
    
    def retrieve_prompts(
        self,
        question: str,
        prompt_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索自定义提示词
        
        根据问题类型匹配提示词
        
        Args:
            question: 用户问题
            prompt_type: 提示词类型（可选）
            limit: 返回的最大数量
            
        Returns:
            提示词列表，按优先级排序
        """
        try:
            query = self.db.query(CustomPrompt).filter(
                CustomPrompt.is_active == True
            )
            
            # 如果指定了类型，进行筛选
            if prompt_type:
                query = query.filter(CustomPrompt.prompt_type == prompt_type)
            
            # 按优先级排序
            prompts = query.order_by(
                CustomPrompt.priority.desc(),
                CustomPrompt.created_at.desc()
            ).limit(limit).all()
            
            results = []
            for prompt in prompts:
                results.append({
                    "id": prompt.id,
                    "name": prompt.name,
                    "prompt_type": prompt.prompt_type,
                    "content": prompt.content,
                    "priority": prompt.priority
                })
            
            logger.info(f"检索到 {len(results)} 个提示词")
            return results
            
        except Exception as e:
            logger.error(f"检索提示词失败: {e}", exc_info=True)
            return []
    
    def retrieve_knowledge(
        self,
        question: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索业务知识库
        
        优先使用向量检索，如果不可用则降级到传统检索
        
        Args:
            question: 用户问题
            category: 分类（可选）
            limit: 返回的最大数量
            
        Returns:
            知识条目列表
        """
        try:
            # 使用向量检索
            if self.use_vector_search:
                try:
                    # 生成查询向量
                    query_embedding = self.embedding_service.generate_embedding(question)
                    
                    # 向量检索
                    results = self.vector_store.search_knowledge(
                        query_embedding=query_embedding,
                        limit=limit,
                        category=category
                    )
                    
                    logger.info(f"向量检索到 {len(results)} 个知识条目")
                    return results
                except Exception as e:
                    logger.warning(f"向量检索失败，降级到传统检索: {e}")
            
            # 传统检索（降级方案）
            query = self.db.query(BusinessKnowledge)
            
            if question:
                query = query.filter(
                    or_(
                        BusinessKnowledge.title.ilike(f"%{question}%"),
                        BusinessKnowledge.content.ilike(f"%{question}%")
                    )
                )
            
            if category:
                query = query.filter(BusinessKnowledge.category == category)
            
            knowledge_items = query.limit(limit).all()
            
            results = []
            for item in knowledge_items:
                results.append({
                    "id": item.id,
                    "title": item.title,
                    "content": item.content,
                    "category": item.category,
                    "tags": item.tags.split(",") if item.tags else [],
                    "similarity": 0.5  # 传统检索没有相似度，给默认值
                })
            
            logger.info(f"传统检索到 {len(results)} 个知识条目")
            return results
            
        except Exception as e:
            logger.error(f"检索业务知识库失败: {e}", exc_info=True)
            return []
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（传统方法，用于降级方案）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度（0-1之间）
        """
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()

