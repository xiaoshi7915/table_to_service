"""
基于pgvector的向量存储服务
使用LangChain的PGVector实现
"""
import warnings
from typing import List, Optional, Dict, Any

# 抑制 PGVector 弃用警告（如果使用旧版本）
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain.*")
warnings.filterwarnings("ignore", message=".*PGVector.*pending deprecation.*", category=UserWarning)

try:
    # LangChain 1.x - 优先使用新版本
    try:
        from langchain_postgres import PGVector
    except ImportError:
        try:
            from langchain_community.vectorstores import PGVector
        except ImportError:
            from langchain.vectorstores import PGVector
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.vectorstores import PGVector

try:
    # LangChain 1.x
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.schema import Document
    from langchain.embeddings.base import Embeddings

from loguru import logger
from app.core.config import settings


class VectorStoreUnavailableError(Exception):
    """向量存储不可用异常（用于优雅降级）"""
    pass


class PGVectorStore:
    """基于pgvector的向量存储"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: Embeddings,
        collection_name: str
    ):
        """
        初始化向量存储
        
        Args:
            connection_string: PostgreSQL连接字符串
            embedding_service: 嵌入服务
            collection_name: 集合名称（表名）
        """
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        
        try:
            # 检查是否是 AnalyticDB PostgreSQL (Greenplum)
            # AnalyticDB 使用 FastANN 向量检索引擎，支持 vector 类型但不需要 pgvector 扩展
            is_analyticdb = False
            try:
                from sqlalchemy import create_engine, text, inspect
                temp_engine = create_engine(connection_string)
                with temp_engine.connect() as conn:
                    result = conn.execute(text("SELECT version()"))
                    version_str = result.scalar() or ""
                    if "Greenplum" in version_str or "AnalyticDB" in version_str:
                        is_analyticdb = True
                        logger.info(f"检测到 AnalyticDB PostgreSQL (Greenplum)，将使用 FastANN 向量检索引擎")
                temp_engine.dispose()
            except:
                pass
            
            # 如果是 AnalyticDB，手动创建 LangChain PGVector 需要的表结构（带分布键）
            if is_analyticdb:
                try:
                    from sqlalchemy import create_engine, text
                    temp_engine = create_engine(connection_string)
                    with temp_engine.connect() as conn:
                        # LangChain PGVector 使用的表名格式
                        # 表名通常是 collection_name 或 langchain_pg_embedding
                        langchain_table_name = f"langchain_pg_embedding"
                        collection_table_name = f"{collection_name}"
                        
                        # 检查表是否已存在
                        result = conn.execute(text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = :table_name
                            )
                        """), {"table_name": collection_table_name})
                        table_exists = result.scalar()
                        
                        if not table_exists:
                            logger.info(f"为 AnalyticDB 创建 LangChain PGVector 表结构: {collection_table_name}")
                            # 创建 LangChain PGVector 需要的表结构（AnalyticDB 兼容，带分布键）
                            # LangChain PGVector 使用的列：uuid, collection_id, embedding, document, cmetadata, custom_id
                            conn.execute(text(f"""
                                CREATE TABLE IF NOT EXISTS "{collection_table_name}" (
                                    uuid UUID PRIMARY KEY,
                                    collection_id UUID,
                                    embedding vector(768),
                                    document TEXT,
                                    cmetadata JSONB,
                                    custom_id VARCHAR
                                ) DISTRIBUTED BY (uuid)
                            """))
                            conn.commit()
                            logger.info(f"✅ 已创建表: {collection_table_name}")
                        else:
                            logger.debug(f"表 {collection_table_name} 已存在")
                    temp_engine.dispose()
                except Exception as e:
                    logger.debug(f"创建 AnalyticDB 表结构时出错（可能已存在）: {e}")
            
            # 创建PGVector实例
            # LangChain 使用 embedding_function 参数
            with warnings.catch_warnings():
                # 抑制弃用警告
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                warnings.filterwarnings("ignore", message=".*PGVector.*pending deprecation.*")
                
                # 如果是 AnalyticDB，不创建扩展（使用 FastANN）
                pgvector_kwargs = {
                    "connection_string": connection_string,
                    "embedding_function": embedding_service,
                    "collection_name": collection_name,
                    "use_jsonb": True,  # 使用JSONB存储元数据
                    "pre_delete_collection": False  # 不删除现有集合
                }
                
                # 检查 PGVector 是否支持 create_extension 参数
                import inspect
                sig = inspect.signature(PGVector.__init__)
                if "create_extension" in sig.parameters:
                    pgvector_kwargs["create_extension"] = not is_analyticdb  # AnalyticDB 不创建扩展
                    if is_analyticdb:
                        logger.info(f"AnalyticDB 模式：跳过 pgvector 扩展创建，使用 FastANN 向量检索引擎")
                
                self.vector_store = PGVector(**pgvector_kwargs)
            logger.info(f"成功初始化向量存储: {collection_name}")
        except Exception as e:
            error_str = str(e)
            # 检查是否是 pgvector 扩展不支持的错误
            if "vector.control" in error_str or ("extension" in error_str.lower() and "vector" in error_str.lower()):
                # pgvector 扩展不支持（如 AnalyticDB PostgreSQL），但可能支持 vector 类型
                # 尝试直接使用 vector 类型（不创建扩展）
                logger.info(f"pgvector扩展不可用，尝试使用 AnalyticDB 的 FastANN 向量检索引擎...")
                try:
                    # 对于 AnalyticDB，LangChain 的 PGVector 可能仍然可以工作（如果 vector 类型可用）
                    # 但需要手动处理扩展创建失败的情况
                    # 这里我们捕获错误，但检查 vector 类型是否可用
                    from sqlalchemy import create_engine, text
                    temp_engine = create_engine(connection_string)
                    with temp_engine.connect() as conn:
                        try:
                            # 测试 vector 类型是否可用（使用正确的语法）
                            test_vector = '[' + ','.join(['0.1'] * 768) + ']'
                            conn.execute(text(f"SELECT '{test_vector}'::vector(768)"))
                            logger.info("vector 类型可用，LangChain PGVector 应该能够工作（即使扩展创建失败）")
                            # vector 类型可用，但 LangChain 的 PGVector 可能在初始化时失败
                            # 尝试直接使用，如果失败则抛出异常
                            raise VectorStoreUnavailableError(f"pgvector扩展不可用，但vector类型可用。LangChain PGVector 可能需要手动配置")
                        except VectorStoreUnavailableError:
                            raise
                        except Exception as type_err:
                            # 检查是否是语法错误（说明类型存在但语法不对）
                            if "syntax" in str(type_err).lower() or "input" in str(type_err).lower():
                                logger.info("vector 类型可用（语法错误说明类型存在），LangChain PGVector 可能能够工作")
                                # vector 类型存在，但我们的测试语法不对，这实际上说明类型是可用的
                                # LangChain 的 PGVector 应该能够工作
                                raise VectorStoreUnavailableError(f"pgvector扩展不可用，但vector类型可用。LangChain PGVector 初始化时可能需要特殊处理")
                            else:
                                logger.warning(f"vector 类型检查失败: {type_err}")
                                raise VectorStoreUnavailableError(f"pgvector扩展和vector类型都不可用: {error_str}")
                    temp_engine.dispose()
                except VectorStoreUnavailableError:
                    raise
                except Exception as check_err:
                    logger.warning(f"检查 vector 类型时出错: {check_err}")
                    raise VectorStoreUnavailableError(f"pgvector扩展不可用: {error_str}")
            else:
                # 其他错误，记录为错误
                logger.error(f"初始化向量存储失败: {e}", exc_info=True)
                raise
    
    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: LangChain Document对象列表
            ids: 文档ID列表（可选）
            
        Returns:
            添加的文档ID列表
        """
        try:
            return self.vector_store.add_documents(
                documents=documents,
                ids=ids
            )
        except Exception as e:
            logger.error(f"添加文档失败: {e}", exc_info=True)
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回数量
            filter: 过滤条件（元数据过滤）
            
        Returns:
            相关文档列表
        """
        try:
            return self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}", exc_info=True)
            return []
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[tuple]:
        """
        相似度搜索（带分数）
        
        Args:
            query: 查询文本
            k: 返回数量
            filter: 过滤条件
            
        Returns:
            (Document, score)元组列表
        """
        try:
            return self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
        except Exception as e:
            logger.error(f"相似度搜索（带分数）失败: {e}", exc_info=True)
            return []
    
    def as_retriever(self, **kwargs):
        """
        转换为检索器
        
        Args:
            **kwargs: 检索器参数
            
        Returns:
            LangChain检索器对象
        """
        return self.vector_store.as_retriever(**kwargs)
    
    def delete(self, ids: Optional[List[str]] = None):
        """
        删除文档
        
        Args:
            ids: 要删除的文档ID列表（如果为None，删除所有）
        """
        try:
            if ids:
                self.vector_store.delete(ids=ids)
            else:
                # 删除整个集合
                self.vector_store.delete_collection()
            logger.info(f"删除文档成功: {ids or 'all'}")
        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
            raise


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_service: Embeddings
    ):
        """
        初始化管理器
        
        Args:
            connection_string: PostgreSQL连接字符串
            embedding_service: 嵌入服务
        """
        self.connection_string = connection_string
        self.embedding_service = embedding_service
        
        # 创建各个集合的向量存储（优雅处理失败）
        self.stores = {}
        for store_type, collection_name in [
            ("terminologies", "terminologies"),
            ("sql_examples", "sql_examples"),
            ("knowledge", "knowledge")
        ]:
            try:
                self.stores[store_type] = PGVectorStore(
                    connection_string=connection_string,
                    embedding_service=embedding_service,
                    collection_name=collection_name
                )
            except VectorStoreUnavailableError:
                # pgvector 不可用，跳过该存储（系统会使用简化检索模式）
                logger.debug(f"向量存储 {store_type} 不可用，将使用简化检索模式")
                self.stores[store_type] = None
            except Exception as e:
                # 其他错误，记录但不阻止初始化
                logger.warning(f"初始化向量存储 {store_type} 失败: {e}，将使用简化检索模式")
                self.stores[store_type] = None
    
    def get_store(self, store_type: str) -> Optional[PGVectorStore]:
        """
        获取指定类型的向量存储
        
        Args:
            store_type: 存储类型（terminologies/sql_examples/knowledge）
            
        Returns:
            向量存储对象，如果不可用则返回 None
        """
        if store_type not in self.stores:
            raise ValueError(f"未知的存储类型: {store_type}")
        return self.stores.get(store_type)


