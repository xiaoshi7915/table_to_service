"""
健康检查器
检查 CocoIndex 各组件的健康状态
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.cocoindex.config import cocoindex_config
from app.core.database import get_local_db


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        初始化健康检查器
        
        Args:
            db_session: 数据库会话
        """
        self.db_session = db_session
    
    def check_all(self) -> Dict[str, Any]:
        """
        检查所有组件的健康状态
        
        Returns:
            健康状态字典
        """
        results = {
            "overall": "healthy",
            "components": {}
        }
        
        # 检查数据库连接
        db_status = self.check_database()
        results["components"]["database"] = db_status
        
        # 检查 pgvector 扩展
        pgvector_status = self.check_pgvector()
        results["components"]["pgvector"] = pgvector_status
        
        # 检查文档存储
        storage_status = self.check_storage()
        results["components"]["storage"] = storage_status
        
        # 检查索引
        index_status = self.check_indexes()
        results["components"]["indexes"] = index_status
        
        # 检查数据源
        source_status = self.check_sources()
        results["components"]["sources"] = source_status
        
        # 判断整体健康状态
        if any(comp.get("status") != "healthy" for comp in results["components"].values()):
            results["overall"] = "degraded"
        
        if any(comp.get("status") == "unhealthy" for comp in results["components"].values()):
            results["overall"] = "unhealthy"
        
        return results
    
    def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            if not self.db_session:
                db_gen = get_local_db()
                db = next(db_gen)
                try:
                    db.execute(text("SELECT 1"))
                    return {"status": "healthy", "message": "数据库连接正常"}
                finally:
                    db.close()
            else:
                self.db_session.execute(text("SELECT 1"))
                return {"status": "healthy", "message": "数据库连接正常"}
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return {"status": "unhealthy", "message": f"数据库连接失败: {str(e)}"}
    
    def check_pgvector(self) -> Dict[str, Any]:
        """检查 pgvector 扩展"""
        try:
            if not self.db_session:
                db_gen = get_local_db()
                db = next(db_gen)
                try:
                    result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
                    ext = result.fetchone()
                    if ext:
                        return {"status": "healthy", "message": "pgvector 扩展已安装"}
                    else:
                        return {"status": "degraded", "message": "pgvector 扩展未安装"}
                finally:
                    db.close()
            else:
                result = self.db_session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
                ext = result.fetchone()
                if ext:
                    return {"status": "healthy", "message": "pgvector 扩展已安装"}
                else:
                    return {"status": "degraded", "message": "pgvector 扩展未安装"}
        except Exception as e:
            logger.error(f"pgvector 检查失败: {e}")
            return {"status": "degraded", "message": f"pgvector 检查失败: {str(e)}"}
    
    def check_storage(self) -> Dict[str, Any]:
        """检查文档存储"""
        try:
            from pathlib import Path
            from app.core.config import settings
            
            storage_path = Path(settings.DOCUMENT_STORAGE_PATH or "/tmp/documents")
            temp_path = Path(settings.DOCUMENT_STORAGE_PATH or "/tmp/documents") / "temp"
            
            if storage_path.exists() and storage_path.is_dir():
                # 检查可写性
                test_file = storage_path / ".test_write"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    writable = True
                except Exception:
                    writable = False
                
                if writable:
                    return {"status": "healthy", "message": "文档存储正常"}
                else:
                    return {"status": "degraded", "message": "文档存储目录不可写"}
            else:
                return {"status": "degraded", "message": "文档存储目录不存在"}
        except Exception as e:
            logger.error(f"存储检查失败: {e}")
            return {"status": "degraded", "message": f"存储检查失败: {str(e)}"}
    
    def check_indexes(self) -> Dict[str, Any]:
        """检查索引状态"""
        try:
            from app.models import DocumentChunk
            from app.core.database import LocalSessionLocal
            
            if not self.db_session:
                db = LocalSessionLocal()
                try:
                    total_chunks = db.query(DocumentChunk).count()
                    chunks_with_embedding = db.query(DocumentChunk).filter(
                        DocumentChunk.embedding.isnot(None)
                    ).count()
                    
                    if total_chunks == 0:
                        return {"status": "healthy", "message": "暂无数据"}
                    
                    embedding_rate = chunks_with_embedding / total_chunks if total_chunks > 0 else 0
                    
                    if embedding_rate >= 0.9:
                        return {"status": "healthy", "message": f"索引状态良好 ({embedding_rate:.1%} 有向量)"}
                    elif embedding_rate >= 0.5:
                        return {"status": "degraded", "message": f"索引状态一般 ({embedding_rate:.1%} 有向量)"}
                    else:
                        return {"status": "degraded", "message": f"索引状态较差 ({embedding_rate:.1%} 有向量)"}
                finally:
                    db.close()
            else:
                total_chunks = self.db_session.query(DocumentChunk).count()
                chunks_with_embedding = self.db_session.query(DocumentChunk).filter(
                    DocumentChunk.embedding.isnot(None)
                ).count()
                
                if total_chunks == 0:
                    return {"status": "healthy", "message": "暂无数据"}
                
                embedding_rate = chunks_with_embedding / total_chunks if total_chunks > 0 else 0
                
                if embedding_rate >= 0.9:
                    return {"status": "healthy", "message": f"索引状态良好 ({embedding_rate:.1%} 有向量)"}
                elif embedding_rate >= 0.5:
                    return {"status": "degraded", "message": f"索引状态一般 ({embedding_rate:.1%} 有向量)"}
                else:
                    return {"status": "degraded", "message": f"索引状态较差 ({embedding_rate:.1%} 有向量)"}
        except Exception as e:
            logger.error(f"索引检查失败: {e}")
            return {"status": "degraded", "message": f"索引检查失败: {str(e)}"}
    
    def check_sources(self) -> Dict[str, Any]:
        """检查数据源状态"""
        try:
            from app.models import DataSourceConfig
            from app.core.database import LocalSessionLocal
            
            if not self.db_session:
                db = LocalSessionLocal()
                try:
                    total_sources = db.query(DataSourceConfig).filter(
                        DataSourceConfig.is_deleted == False
                    ).count()
                    enabled_sources = db.query(DataSourceConfig).filter(
                        DataSourceConfig.is_deleted == False,
                        DataSourceConfig.sync_enabled == True
                    ).count()
                    
                    return {
                        "status": "healthy",
                        "message": f"数据源状态正常 ({enabled_sources}/{total_sources} 已启用)",
                        "total": total_sources,
                        "enabled": enabled_sources
                    }
                finally:
                    db.close()
            else:
                total_sources = self.db_session.query(DataSourceConfig).filter(
                    DataSourceConfig.is_deleted == False
                ).count()
                enabled_sources = self.db_session.query(DataSourceConfig).filter(
                    DataSourceConfig.is_deleted == False,
                    DataSourceConfig.sync_enabled == True
                ).count()
                
                return {
                    "status": "healthy",
                    "message": f"数据源状态正常 ({enabled_sources}/{total_sources} 已启用)",
                    "total": total_sources,
                    "enabled": enabled_sources
                }
        except Exception as e:
            logger.error(f"数据源检查失败: {e}")
            return {"status": "degraded", "message": f"数据源检查失败: {str(e)}"}

