"""
初始化pgvector向量存储
将现有知识库数据导入到 PostgreSQL pgvector 向量存储
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from loguru import logger
from app.core.database import get_local_db
from app.models import Terminology, SQLExample, BusinessKnowledge
from app.core.rag_langchain.vector_store import VectorStoreManager, VectorStoreUnavailableError
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService
from app.core.config import settings

try:
    # LangChain 1.x
    from langchain_core.documents import Document
except ImportError:
    # LangChain 0.x (fallback)
    from langchain.schema import Document


def init_vector_store():
    """
    初始化pgvector向量存储
    将现有数据导入到 PostgreSQL pgvector 向量存储
    """
    logger.info("开始初始化pgvector向量存储...")
    
    # 检查数据库类型
    connection_string = settings.local_database_url
    if "postgresql" not in connection_string.lower():
        logger.error("pgvector需要PostgreSQL数据库，当前配置不是PostgreSQL")
        logger.info(f"当前数据库URL: {connection_string}")
        logger.info("请将LOCAL_DB_TYPE设置为postgresql")
        return False
    
    try:
        # 初始化嵌入服务
        logger.info("初始化中文嵌入模型...")
        embedding_service = ChineseEmbeddingService()
        
        # 初始化向量存储管理器
        logger.info("初始化向量存储管理器...")
        try:
            vector_manager = VectorStoreManager(connection_string, embedding_service)
            logger.info("✅ 向量存储管理器初始化成功")
        except VectorStoreUnavailableError as e:
            logger.error(f"pgvector扩展不可用: {e}")
            logger.info("请先运行: python scripts/init_pgvector.py 来初始化pgvector扩展")
            return False
        except Exception as e:
            logger.error(f"初始化向量存储管理器失败: {e}", exc_info=True)
            return False
        
        # 获取数据库会话
        db: Session = next(get_local_db())
        
        try:
            # 1. 导入术语库
            logger.info("导入术语库...")
            terminologies = db.query(Terminology).all()
            logger.info(f"找到 {len(terminologies)} 个术语")
            
            if terminologies:
                term_store = vector_manager.get_store("terminologies")
                if term_store:
                    term_docs = []
                    for term in terminologies:
                        # 构建文档内容
                        doc_text = f"{term.business_term}"
                        if term.description:
                            doc_text += f" {term.description}"
                        if term.db_field:
                            doc_text += f" 字段: {term.db_field}"
                        if term.table_name:
                            doc_text += f" 表: {term.table_name}"
                        
                        # 创建 LangChain Document
                        metadata = {
                            "terminology_id": term.id,
                            "business_term": term.business_term,
                            "db_field": term.db_field or "",
                            "table_name": term.table_name or "",
                            "description": term.description or "",
                            "category": term.category or ""
                        }
                        term_docs.append(Document(page_content=doc_text.strip(), metadata=metadata))
                    
                    # 批量添加文档
                    if term_docs:
                        try:
                            term_store.add_documents(term_docs)
                            logger.info(f"✅ 成功导入 {len(term_docs)} 个术语到向量存储")
                        except Exception as e:
                            logger.warning(f"导入术语到向量存储失败: {e}")
                else:
                    logger.warning("术语库向量存储不可用，跳过")
            
            # 2. 导入SQL示例
            logger.info("导入SQL示例...")
            sql_examples = db.query(SQLExample).all()
            logger.info(f"找到 {len(sql_examples)} 个SQL示例")
            
            if sql_examples:
                sql_store = vector_manager.get_store("sql_examples")
                if sql_store:
                    sql_docs = []
                    for example in sql_examples:
                        # 构建文档内容
                        doc_text = f"问题: {example.question}"
                        if example.description:
                            doc_text += f"\n描述: {example.description}"
                        if example.sql_statement:
                            doc_text += f"\nSQL: {example.sql_statement}"
                        
                        # 创建 LangChain Document
                        metadata = {
                            "example_id": example.id,
                            "question": example.question,
                            "sql_statement": example.sql_statement or "",
                            "db_type": example.db_type or "",
                            "table_name": example.table_name or "",
                            "description": example.description or ""
                        }
                        sql_docs.append(Document(page_content=doc_text.strip(), metadata=metadata))
                    
                    # 批量添加文档
                    if sql_docs:
                        try:
                            sql_store.add_documents(sql_docs)
                            logger.info(f"✅ 成功导入 {len(sql_docs)} 个SQL示例到向量存储")
                        except Exception as e:
                            logger.warning(f"导入SQL示例到向量存储失败: {e}")
                else:
                    logger.warning("SQL示例向量存储不可用，跳过")
            
            # 3. 导入业务知识库
            logger.info("导入业务知识库...")
            knowledge_items = db.query(BusinessKnowledge).all()
            logger.info(f"找到 {len(knowledge_items)} 个知识条目")
            
            if knowledge_items:
                knowledge_store = vector_manager.get_store("knowledge")
                if knowledge_store:
                    knowledge_docs = []
                    for item in knowledge_items:
                        # 构建文档内容
                        doc_text = f"{item.title}"
                        if item.content:
                            doc_text += f"\n{item.content}"
                        
                        # 创建 LangChain Document
                        metadata = {
                            "knowledge_id": item.id,
                            "title": item.title,
                            "content": item.content or "",
                            "category": item.category or "",
                            "tags": item.tags or ""
                        }
                        knowledge_docs.append(Document(page_content=doc_text.strip(), metadata=metadata))
                    
                    # 批量添加文档
                    if knowledge_docs:
                        try:
                            knowledge_store.add_documents(knowledge_docs)
                            logger.info(f"✅ 成功导入 {len(knowledge_docs)} 个知识条目到向量存储")
                        except Exception as e:
                            logger.warning(f"导入知识条目到向量存储失败: {e}")
                else:
                    logger.warning("知识库向量存储不可用，跳过")
            
            logger.info("=" * 50)
            logger.info("pgvector向量存储初始化完成！")
            logger.info(f"  - 术语库: {len(terminologies)} 条")
            logger.info(f"  - SQL示例: {len(sql_examples)} 条")
            logger.info(f"  - 业务知识: {len(knowledge_items)} 条")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"导入数据到向量存储失败: {e}", exc_info=True)
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"初始化向量存储失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    try:
        success = init_vector_store()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)
