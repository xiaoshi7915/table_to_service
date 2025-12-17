"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, Token, ResponseModel
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user_by_username,
    get_current_active_user
)
from app.core.config import settings
from loguru import logger

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/register", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        # 检查用户是否已存在
        existing_user = get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 创建新用户
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            hashed_password=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info("新用户注册: {}", user_data.username)
        
        return ResponseModel(
            success=True,
            message="注册成功",
            data={"username": new_user.username, "id": new_user.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("注册失败: {}", e, exc_info=True)
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {error_msg}"
        )


@router.post("/login", response_model=Token)
async def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        # 记录登录尝试
        logger.debug("登录尝试: 用户名={}", user_data.username)
        
        user = authenticate_user(db, user_data.username, user_data.password)
        if not user:
            logger.warning("登录失败: 用户名或密码错误 - {}", user_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info("用户登录成功: {}", user_data.username)
        
        return Token(access_token=access_token, token_type="bearer")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("登录失败: {}", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.get("/me", response_model=ResponseModel)
async def get_current_user_info(request: Request, current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return ResponseModel(
        success=True,
        message="获取成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    )

