"""
认证和授权模块
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from models import User
from schemas import TokenData
from loguru import logger

# 密码加密上下文
# 使用bcrypt，如果失败则使用sha256_crypt作为备选
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # 测试bcrypt是否可用
    test_hash = pwd_context.hash("test")
except Exception as e:
    logger.warning(f"bcrypt初始化失败，使用sha256_crypt: {e}")
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# OAuth2密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"密码验证失败，尝试备用方案: {e}")
        # 如果bcrypt验证失败，尝试sha256_crypt
        try:
            fallback_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
            return fallback_context.verify(plain_password, hashed_password)
        except Exception as e2:
            logger.error(f"备用密码验证也失败: {e2}")
            return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    try:
        # 确保密码是字符串且不超过72字节（bcrypt限制）
        if isinstance(password, bytes):
            password = password.decode('utf-8')
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"密码哈希失败: {e}")
        # 如果bcrypt失败，尝试使用sha256_crypt
        try:
            fallback_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
            return fallback_context.hash(password)
        except Exception as e2:
            logger.error(f"备用密码哈希也失败: {e2}")
            raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> TokenData:
    """验证令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token中缺少sub字段")
            raise credentials_exception
        token_data = TokenData(username=username)
        return token_data
    except JWTError as e:
        logger.warning(f"Token验证失败: {e}")
        raise credentials_exception


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户（依赖注入）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = verify_token(token, credentials_exception)
        user = get_user_by_username(db, username=token_data.username)
        
        if user is None:
            logger.warning(f"用户不存在: {token_data.username}")
            raise credentials_exception
        
        if not user.is_active:
            logger.warning(f"用户已被禁用: {token_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}", exc_info=True)
        raise credentials_exception


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    return current_user

