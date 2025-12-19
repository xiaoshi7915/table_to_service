"""
初始化向量数据库
将现有知识库数据导入到 Chroma 向量数据库
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
from app.core.rag.vector_store import VectorStore
from app.core.rag.embedding_service import EmbeddingService, LocalEmbeddingService


def init_vector_store(use_local_embedding: bool = False):
    """
    初始化向量数据库
    
    Args:
        use_local_embedding: 是否使用本地嵌入模型（如果为False，使用OpenAI）
    """
    logger.info("开始初始化向量数据库...")
    
    # 初始化向量数据库
    vector_store = VectorStore()
    
    # 初始化嵌入服务
    if use_local_embedding:
        logger.info("使用本地嵌入模型（sentence-transformers）")
        embedding_service = LocalEmbeddingService()
    else:
        logger.info("使用OpenAI嵌入模型")
        embedding_service = EmbeddingService()
    
    # 获取数据库会话
    db: Session = next(get_local_db())
    
    try:
        # 1. 导入术语库
        logger.info("导入术语库...")
        terminologies = db.query(Terminology).all()
        logger.info(f"找到 {len(terminologies)} 个术语")
        
        for term in terminologies:
            try:
                # 生成嵌入向量
                doc_text = f"{term.business_term} {term.description or ''} {term.db_field} {term.table_name or ''}".strip()
                embedding = embedding_service.generate_embedding(doc_text)
                
                # 添加到向量数据库
                vector_store.add_terminology(
                    terminology_id=str(term.id),
                    business_term=term.business_term,
                    db_field=term.db_field,
                    table_name=term.table_name,
                    description=term.description,
                    embedding=embedding
                )
            except Exception as e:
                logger.warning(f"导入术语 {term.id} 失败: {e}")
        
        logger.info(f"成功导入 {len(terminologies)} 个术语")
        
        # 2. 导入SQL示例
        logger.info("导入SQL示例...")
        sql_examples = db.query(SQLExample).all()
        logger.info(f"找到 {len(sql_examples)} 个SQL示例")
        
        for example in sql_examples:
            try:
                # 生成嵌入向量
                doc_text = f"{example.question} {example.description or ''} {example.sql_statement}".strip()
                embedding = embedding_service.generate_embedding(doc_text)
                
                # 添加到向量数据库
                vector_store.add_sql_example(
                    example_id=str(example.id),
                    question=example.question,
                    sql_statement=example.sql_statement,
                    db_type=example.db_type,
                    table_name=example.table_name,
                    description=example.description,
                    embedding=embedding
                )
            except Exception as e:
                logger.warning(f"导入SQL示例 {example.id} 失败: {e}")
        
        logger.info(f"成功导入 {len(sql_examples)} 个SQL示例")
        
        # 3. 导入业务知识库
        logger.info("导入业务知识库...")
        knowledge_items = db.query(BusinessKnowledge).all()
        logger.info(f"找到 {len(knowledge_items)} 个知识条目")
        
        for item in knowledge_items:
            try:
                # 生成嵌入向量
                doc_text = f"{item.title} {item.content}".strip()
                embedding = embedding_service.generate_embedding(doc_text)
                
                # 添加到向量数据库
                vector_store.add_knowledge(
                    knowledge_id=str(item.id),
                    title=item.title,
                    content=item.content,
                    category=item.category,
                    tags=item.tags,
                    embedding=embedding
                )
            except Exception as e:
                logger.warning(f"导入知识条目 {item.id} 失败: {e}")
        
        logger.info(f"成功导入 {len(knowledge_items)} 个知识条目")
        
        logger.info("=" * 50)
        logger.info("向量数据库初始化完成！")
        logger.info(f"  - 术语库: {len(terminologies)} 条")
        logger.info(f"  - SQL示例: {len(sql_examples)} 条")
        logger.info(f"  - 业务知识: {len(knowledge_items)} 条")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"初始化向量数据库失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="初始化向量数据库")
    parser.add_argument(
        "--use-local",
        action="store_true",
        help="使用本地嵌入模型（sentence-transformers）而不是OpenAI"
    )
    
    args = parser.parse_args()
    
    try:
        init_vector_store(use_local_embedding=args.use_local)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


