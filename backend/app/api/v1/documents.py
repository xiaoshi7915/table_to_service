"""
文档管理路由
支持文档上传、解析、索引和管理
"""
import hashlib
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_local_db
from app.models import User, Document, DocumentChunk
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.cocoindex.config import cocoindex_config
from app.core.cocoindex.sync.document_processor import DocumentProcessor
from app.core.cocoindex.parsers.parser_factory import ParserFactory
from app.core.rag_langchain.embedding_service import ChineseEmbeddingService


router = APIRouter(prefix="/api/v1/documents", tags=["文档管理"])


# ==================== 请求/响应模型 ====================

class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    title: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str = ""
    updated_at: str = ""


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ==================== 辅助函数 ====================

def calculate_file_hash(file_path: Path) -> str:
    """计算文件哈希值"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def save_uploaded_file(file: UploadFile, storage_path: Path) -> Path:
    """保存上传的文件"""
    # 确保存储目录存在
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名（避免冲突）
    file_path = storage_path / file.filename
    
    # 如果文件已存在，添加序号
    counter = 1
    while file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        file_path = storage_path / f"{stem}_{counter}{suffix}"
        counter += 1
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path


async def process_document(
    document_id: int,
    file_path: str
):
    """
    异步处理文档：解析、分块、向量化、索引
    
    Args:
        document_id: 文档ID
        file_path: 文件路径
    """
    from app.core.database import LocalSessionLocal
    db = LocalSessionLocal()
    try:
        # 创建嵌入服务
        embedding_service = ChineseEmbeddingService()
        
        # 创建文档处理器
        processor = DocumentProcessor(db=db, embedding_service=embedding_service)
        
        # 处理文档
        result = processor.process_document(document_id)
        
        if not result.get("success"):
            logger.error(f"文档处理失败: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"文档处理失败: {e}", exc_info=True)
        # 更新状态为失败
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                db.commit()
        except Exception as db_error:
            logger.error(f"更新文档状态失败: {db_error}")
            db.rollback()
    finally:
        db.close()


# ==================== API路由 ====================

@router.post("/upload", response_model=ResponseModel)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="上传的文件"),
    category: Optional[str] = Query(None, description="文档分类"),
    tags: Optional[str] = Query(None, description="文档标签（逗号分隔）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """上传文档"""
    try:
        # 检查文件类型
        file_ext = Path(file.filename).suffix.lower()
        if not ParserFactory.is_supported(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(ParserFactory.get_supported_extensions())}"
            )
        
        # 检查文件大小
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置到开头
        
        if file_size > cocoindex_config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB，最大允许: {cocoindex_config.MAX_FILE_SIZE / 1024 / 1024:.2f}MB"
            )
        
        # 保存文件
        storage_path = cocoindex_config.get_document_storage_path()
        saved_path = save_uploaded_file(file, storage_path)
        
        # 计算文件哈希
        content_hash = calculate_file_hash(saved_path)
        
        # 检查是否已存在相同内容的文档
        existing = db.query(Document).filter(
            Document.content_hash == content_hash,
            Document.is_deleted == False
        ).first()
        
        if existing:
            # 删除刚保存的文件（重复）
            saved_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"文档已存在: {existing.filename}"
            )
        
        # 创建文档记录
        document = Document(
            filename=file.filename,
            file_type=file_ext[1:] if file_ext.startswith('.') else file_ext,
            file_path=str(saved_path),
            file_size=file_size,
            content_hash=content_hash,
            status="pending",
            created_by=current_user.id,
            meta_data={
                "category": category,
                "tags": tags.split(",") if tags else []
            } if category or tags else None
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 异步处理文档（后台任务会自动创建新的数据库会话）
        background_tasks.add_task(process_document, document.id, str(saved_path))
        
        logger.info(f"用户 {current_user.username} 上传文档: {file.filename} (ID: {document.id})")
        
        return ResponseModel(
            success=True,
            message="文档上传成功，正在处理中",
            data={
                "id": document.id,
                "filename": document.filename,
                "status": document.status
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"文档上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档上传失败: {str(e)}"
        )


@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_documents(
    keyword: Optional[str] = Query(None, description="搜索关键词（文件名或标题）"),
    file_type: Optional[str] = Query(None, description="文件类型筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取文档列表"""
    try:
        query = db.query(Document).filter(Document.is_deleted == False)
        
        # 关键词搜索
        if keyword:
            query = query.filter(
                (Document.filename.ilike(f"%{keyword}%")) |
                (Document.title.ilike(f"%{keyword}%"))
            )
        
        # 文件类型筛选
        if file_type:
            query = query.filter(Document.file_type == file_type)
        
        # 状态筛选
        if status:
            query = query.filter(Document.status == status)
        
        # 总数
        total = query.count()
        
        # 分页
        documents = query.order_by(Document.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # 转换为响应格式
        document_list = []
        for doc in documents:
            try:
                doc_response = DocumentResponse(
                    id=doc.id,
                    filename=doc.filename or "",
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    title=doc.title,
                    status=doc.status or "pending",
                    metadata=doc.meta_data,
                    created_at=doc.created_at.isoformat() if doc.created_at else "",
                    updated_at=doc.updated_at.isoformat() if doc.updated_at else ""
                )
                document_list.append(doc_response)
            except Exception as e:
                logger.warning(f"转换文档响应失败 (ID: {doc.id}): {e}")
                # 使用字典格式作为后备
                document_list.append({
                    "id": doc.id,
                    "filename": doc.filename or "",
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "title": doc.title or doc.filename or "",
                    "status": doc.status or "pending",
                    "metadata": doc.meta_data,
                    "created_at": doc.created_at.isoformat() if doc.created_at else "",
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else ""
                })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "documents": document_list,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.get("/{document_id}", response_model=ResponseModel)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取文档详情"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 获取分块信息
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "file_path": document.file_path,
                "title": document.title,
                "status": document.status,
                "metadata": document.meta_data,
                "chunks_count": len(chunks),
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "updated_at": document.updated_at.isoformat() if document.updated_at else ""
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档详情失败: {str(e)}"
        )


@router.delete("/{document_id}", response_model=ResponseModel)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除文档（软删除）"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 软删除
        document.is_deleted = True
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除文档: {document.filename} (ID: {document_id})")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )

