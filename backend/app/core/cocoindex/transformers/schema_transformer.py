"""
数据库 Schema 数据转换器
将数据库表结构转换为 Document 格式
"""
from typing import Dict, Any, List
from loguru import logger

from .base_transformer import BaseTransformer


class SchemaTransformer(BaseTransformer):
    """数据库 Schema 数据转换器"""
    
    def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        转换 Schema 数据
        
        Args:
            data: Schema 数据，包含表结构信息
            
        Returns:
            Document 列表
        """
        table_name = data.get("table_name", "")
        columns = data.get("columns", [])
        primary_keys = data.get("primary_keys", [])
        foreign_keys = data.get("foreign_keys", [])
        
        # 构建表结构描述
        content_parts = [f"表名: {table_name}"]
        
        if columns:
            content_parts.append("\n字段列表:")
            for col in columns:
                col_desc = f"  - {col['name']} ({col['type']})"
                if not col.get("nullable", True):
                    col_desc += " NOT NULL"
                if col.get("default"):
                    col_desc += f" DEFAULT {col['default']}"
                if col.get("comment"):
                    col_desc += f" COMMENT '{col['comment']}'"
                content_parts.append(col_desc)
        
        if primary_keys:
            content_parts.append(f"\n主键: {', '.join(primary_keys)}")
        
        if foreign_keys:
            content_parts.append("\n外键:")
            for fk in foreign_keys:
                fk_desc = f"  - {fk['name']}: {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}"
                content_parts.append(fk_desc)
        
        content = "\n".join(content_parts)
        
        metadata = {
            "source_type": "database_schema",
            "table_name": table_name,
            "schema": data.get("schema"),
            "db_config_id": data.get("_db_config_id"),
            "columns_count": len(columns),
            "primary_keys": primary_keys,
        }
        
        embedding = self.generate_embedding(content) if content else None
        
        return [{
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }]

