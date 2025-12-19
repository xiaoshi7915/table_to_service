"""
数据库密码加密模块
使用Fernet对称加密，因为需要解密密码用于数据库连接
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
from app.core.config import settings
from loguru import logger

# 从配置中获取加密密钥，如果没有则生成一个（注意：生产环境应该使用固定的密钥）
ENCRYPTION_KEY = os.getenv("DB_PASSWORD_ENCRYPTION_KEY", "")

if not ENCRYPTION_KEY:
    # 如果没有配置密钥，使用SECRET_KEY生成一个固定的密钥
    # 注意：这不是最佳实践，生产环境应该使用独立的加密密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'db_password_salt',  # 固定salt，生产环境应该使用随机salt
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    ENCRYPTION_KEY = key.decode()
    logger.warning("使用SECRET_KEY生成数据库密码加密密钥，生产环境建议配置DB_PASSWORD_ENCRYPTION_KEY环境变量")
else:
    # 如果配置了密钥，直接使用
    try:
        ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
    except:
        pass

# 创建Fernet实例
try:
    fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception as e:
    logger.error("初始化Fernet加密器失败: {}", e)
    # 如果失败，尝试使用默认密钥
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'db_password_salt',
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        fernet = Fernet(key)
    except Exception as e2:
        logger.error("使用备用方法初始化Fernet也失败: {}", e2)
        raise


def encrypt_password(password: str) -> str:
    """
    加密数据库密码
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码（base64编码）
    """
    if not password:
        return ""
    
    try:
        # 加密密码
        encrypted = fernet.encrypt(password.encode())
        # 返回base64编码的字符串
        return encrypted.decode()
    except Exception as e:
        logger.error("加密密码失败: {}", e)
        raise ValueError(f"密码加密失败: {str(e)}")


def decrypt_password(encrypted_password: str) -> str:
    """
    解密数据库密码
    
    Args:
        encrypted_password: 加密后的密码（base64编码）
        
    Returns:
        明文密码
    """
    if not encrypted_password:
        return ""
    
    try:
        # 尝试解密
        decrypted = fernet.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        # 如果解密失败，可能是旧数据（明文存储），直接返回
        logger.warning("解密密码失败，可能是明文存储的旧数据: {}", e)
        return encrypted_password


def is_encrypted(password: str) -> bool:
    """
    判断密码是否已加密
    
    Args:
        password: 密码字符串
        
    Returns:
        是否已加密
    """
    if not password:
        return False
    
    try:
        # 尝试解密，如果成功则说明已加密
        fernet.decrypt(password.encode())
        return True
    except:
        # 解密失败，说明可能是明文
        return False

