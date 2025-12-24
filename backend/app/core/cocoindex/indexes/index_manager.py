"""
索引管理器
统一管理所有索引的创建、更新和查询
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.cocoindex.config import cocoindex_config
from app.core.database import get_local_db


class IndexManager:
    """索引管理器"""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        初始化索引管理器
        
        Args:
            db_session: 数据库会话
        """
        self.db_session = db_session
    
    def create_vector_index(
        self,
        table_name: str,
        column_name: str = "embedding",
        dimension: int = 768,
        metric: str = "cosine"
    ) -> bool:
        """
        创建向量索引
        
        Args:
            table_name: 表名
            column_name: 向量列名
            dimension: 向量维度
            metric: 相似度度量（cosine, l2, inner_product）
            
        Returns:
            是否成功
        """
        if not self.db_session:
            logger.warning("数据库会话未提供，无法创建索引")
            return False
        
        try:
            # 检查 pgvector 扩展是否已安装
            self.db_session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.db_session.commit()
            
            # 构建索引名称
            index_name = f"idx_{table_name}_{column_name}_vector"
            
            # 选择索引类型和操作符
            if metric == "cosine":
                ops = "vector_cosine_ops"
            elif metric == "l2":
                ops = "vector_l2_ops"
            else:  # inner_product
                ops = "vector_ip_ops"
            
            # 创建 ivfflat 索引（需要先有数据）
            # 注意：ivfflat 索引需要指定 lists 参数，通常设置为 sqrt(行数)
            sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table_name}
            USING ivfflat ({column_name} {ops})
            WITH (lists = 100)
            """
            
            self.db_session.execute(text(sql))
            self.db_session.commit()
            
            logger.info(f"向量索引创建成功: {index_name}")
            return True
        except Exception as e:
            logger.error(f"创建向量索引失败: {e}", exc_info=True)
            self.db_session.rollback()
            return False
    
    def create_metadata_index(self, table_name: str, column_name: str = "metadata") -> bool:
        """
        创建元数据 GIN 索引
        
        Args:
            table_name: 表名
            column_name: 元数据列名
            
        Returns:
            是否成功
        """
        if not self.db_session:
            return False
        
        try:
            index_name = f"idx_{table_name}_{column_name}_gin"
            sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table_name}
            USING gin ({column_name} jsonb_path_ops)
            """
            
            self.db_session.execute(text(sql))
            self.db_session.commit()
            
            logger.info(f"元数据索引创建成功: {index_name}")
            return True
        except Exception as e:
            logger.error(f"创建元数据索引失败: {e}", exc_info=True)
            self.db_session.rollback()
            return False
    
    def ensure_indexes(self, collection_name: str) -> bool:
        """
        确保集合的所有索引已创建
        
        Args:
            collection_name: 集合名称
            
        Returns:
            是否成功
        """
        # 根据集合名称确定表名
        table_mapping = {
            "knowledge": "document_chunks",
            "terminologies": "document_chunks",
            "sql_examples": "document_chunks",
            "documents": "document_chunks",
            "schemas": "document_chunks",
        }
        
        table_name = table_mapping.get(collection_name, "document_chunks")
        
        # 创建向量索引
        vector_success = self.create_vector_index(
            table_name=table_name,
            column_name="embedding",
            dimension=cocoindex_config.EMBEDDING_DIMENSION
        )
        
        # 创建元数据索引
        metadata_success = self.create_metadata_index(
            table_name=table_name,
            column_name="metadata"
        )
        
        return vector_success and metadata_success
    
    def get_index_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的索引信息
        
        Args:
            table_name: 表名
            
        Returns:
            索引信息字典
        """
        if not self.db_session:
            return {}
        
        try:
            sql = """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = :table_name
            """
            
            result = self.db_session.execute(text(sql), {"table_name": table_name})
            indexes = result.fetchall()
            
            return {
                "table_name": table_name,
                "indexes": [
                    {"name": idx[0], "definition": idx[1]}
                    for idx in indexes
                ],
                "count": len(indexes)
            }
        except Exception as e:
            logger.error(f"获取索引信息失败: {e}")
            return {}

