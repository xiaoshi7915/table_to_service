"""
知识库数据转换器
将术语库、SQL示例、自定义提示词转换为 Document 格式
"""
from typing import Dict, Any, List
from loguru import logger

from .base_transformer import BaseTransformer


class KnowledgeTransformer(BaseTransformer):
    """知识库数据转换器"""
    
    def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        转换知识库数据
        
        Args:
            data: 原始数据，包含 _source_table 字段标识来源表
            
        Returns:
            Document 列表
        """
        source_table = data.get("_source_table", "")
        
        # 根据来源表构建不同的文档内容
        if source_table == "terminologies":
            return self._transform_terminology(data)
        elif source_table == "sql_examples":
            return self._transform_sql_example(data)
        elif source_table == "custom_prompts":
            return self._transform_prompt(data)
        else:
            # 通用转换
            return self._transform_generic(data)
    
    def _transform_terminology(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换术语库数据"""
        content_parts = []
        
        if data.get("business_term"):
            content_parts.append(f"业务术语: {data['business_term']}")
        if data.get("description"):
            content_parts.append(f"描述: {data['description']}")
        if data.get("db_field"):
            content_parts.append(f"数据库字段: {data['db_field']}")
        if data.get("table_name"):
            content_parts.append(f"表名: {data['table_name']}")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "source_type": "terminology",
            "terminology_id": data.get("id"),
            "business_term": data.get("business_term"),
            "db_field": data.get("db_field"),
            "table_name": data.get("table_name"),
        }
        
        embedding = self.generate_embedding(content) if content else None
        
        return [{
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }]
    
    def _transform_sql_example(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换SQL示例数据"""
        content_parts = []
        
        if data.get("question"):
            content_parts.append(f"问题: {data['question']}")
        if data.get("sql_statement"):
            content_parts.append(f"SQL: {data['sql_statement']}")
        if data.get("description"):
            content_parts.append(f"说明: {data['description']}")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "source_type": "sql_example",
            "sql_example_id": data.get("id"),
            "question": data.get("question"),
            "db_type": data.get("db_type"),
            "table_name": data.get("table_name"),
        }
        
        embedding = self.generate_embedding(content) if content else None
        
        return [{
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }]
    
    def _transform_prompt(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换自定义提示词数据"""
        content_parts = []
        
        if data.get("name"):
            content_parts.append(f"提示词名称: {data['name']}")
        if data.get("content"):
            content_parts.append(f"内容: {data['content']}")
        if data.get("prompt_type"):
            content_parts.append(f"类型: {data['prompt_type']}")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "source_type": "custom_prompt",
            "prompt_id": data.get("id"),
            "name": data.get("name"),
            "prompt_type": data.get("prompt_type"),
            "priority": data.get("priority"),
        }
        
        embedding = self.generate_embedding(content) if content else None
        
        return [{
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }]
    
    def _transform_generic(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """通用转换"""
        # 尝试构建内容
        content_parts = []
        for key, value in data.items():
            if key.startswith("_") or value is None:
                continue
            if isinstance(value, (str, int, float)):
                content_parts.append(f"{key}: {value}")
        
        content = "\n".join(content_parts)
        
        metadata = {
            "source_type": "generic",
            **{k: v for k, v in data.items() if not k.startswith("_")}
        }
        
        embedding = self.generate_embedding(content) if content else None
        
        return [{
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }]

