"""
PostgreSQL + pgvector 索引
使用 CocoIndex 的 Postgres Target
"""
from typing import Dict, Any, Optional, List
from loguru import logger

try:
    import cocoindex
    from cocoindex.targets import Postgres
    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False
    logger.warning("cocoindex 未安装，索引功能将不可用")

from app.core.cocoindex.config import cocoindex_config
from app.core.cocoindex.utils.connection_parser import parse_connection_string


class PostgresIndex:
    """PostgreSQL + pgvector 索引"""
    
    def __init__(
        self,
        collection_name: str,
        connection_string: Optional[str] = None,
        dimension: Optional[int] = None
    ):
        """
        初始化索引
        
        Args:
            collection_name: 集合名称
            connection_string: PostgreSQL 连接字符串
            dimension: 向量维度
        """
        self.collection_name = collection_name
        self.connection_string = connection_string or cocoindex_config.POSTGRESQL_CONNECTION_STRING
        self.dimension = dimension or cocoindex_config.EMBEDDING_DIMENSION
        self.use_cocoindex = COCOINDEX_AVAILABLE
        
        # 创建 CocoIndex Postgres Target（如果可用）
        # 注意：Postgres Target 的实际 API 是 Postgres(table_name=..., database=...)
        if COCOINDEX_AVAILABLE:
            try:
                # 解析连接字符串获取数据库配置
                db_spec = parse_connection_string(self.connection_string)
                
                # 创建 Postgres Target
                # 注意：CocoIndex 的 Postgres Target 使用 table_name 参数，不是 collection_name
                self.target = Postgres(
                    table_name=collection_name,  # 使用 collection_name 作为表名
                    database=db_spec  # DatabaseConnectionSpec
                )
                logger.info(f"CocoIndex Postgres Target 创建成功: {collection_name}")
            except Exception as e:
                logger.warning(f"创建 CocoIndex Postgres Target 失败: {e}")
                self.target = None
        else:
            self.target = None
            logger.warning("cocoindex 未安装，PostgresIndex 将使用直接数据库操作")
    
    def create_index(
        self,
        primary_key_fields: List[str],
        vector_indexes: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """
        创建索引
        
        Args:
            primary_key_fields: 主键字段列表
            vector_indexes: 向量索引定义列表
            
        Returns:
            CocoIndex 导出对象
        """
        if not vector_indexes:
            # 默认向量索引配置
            vector_indexes = [{
                "field_name": "embedding",
                "metric": "cosine_similarity",
                "dimension": self.dimension
            }]
        
        # 使用 CocoIndex 创建索引
        # 注意：这里需要根据实际的 CocoIndex API 调整
        logger.info(f"创建索引: {self.collection_name}")
        
        return self.target
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        return {
            "collection_name": self.collection_name,
            "dimension": self.dimension,
            "connection_string": self.connection_string[:50] + "..." if len(self.connection_string) > 50 else self.connection_string
        }

