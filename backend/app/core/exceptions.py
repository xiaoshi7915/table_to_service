"""
自定义异常类
用于统一错误处理和响应格式
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class BaseAPIException(HTTPException):
    """基础API异常类"""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常
        
        Args:
            status_code: HTTP状态码
            message: 错误消息（用户友好）
            detail: 详细错误信息（调试用）
            error_code: 错误代码（用于前端处理）
            data: 额外数据
        """
        self.message = message
        self.error_code = error_code
        self.data = data or {}
        super().__init__(status_code=status_code, detail=detail or message)


class ValidationError(BaseAPIException):
    """参数验证错误"""
    
    def __init__(self, message: str = "请求参数验证失败", detail: Optional[str] = None, errors: Optional[list] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            detail=detail,
            error_code="VALIDATION_ERROR",
            data={"errors": errors} if errors else {}
        )


class NotFoundError(BaseAPIException):
    """资源未找到错误"""
    
    def __init__(self, message: str = "资源未找到", detail: Optional[str] = None, resource_type: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            detail=detail,
            error_code="NOT_FOUND",
            data={"resource_type": resource_type} if resource_type else {}
        )


class UnauthorizedError(BaseAPIException):
    """未授权错误"""
    
    def __init__(self, message: str = "未授权访问", detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenError(BaseAPIException):
    """禁止访问错误"""
    
    def __init__(self, message: str = "禁止访问", detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            detail=detail,
            error_code="FORBIDDEN"
        )


class InternalServerError(BaseAPIException):
    """服务器内部错误"""
    
    def __init__(self, message: str = "服务器内部错误", detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            detail=detail,
            error_code="INTERNAL_ERROR"
        )


class DatabaseError(BaseAPIException):
    """数据库错误"""
    
    def __init__(self, message: str = "数据库操作失败", detail: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class SQLExecutionError(BaseAPIException):
    """SQL执行错误"""
    
    def __init__(self, message: str = "SQL执行失败", detail: Optional[str] = None, sql: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            detail=detail,
            error_code="SQL_EXECUTION_ERROR",
            data={"sql": sql[:200] + "..." if sql and len(sql) > 200 else sql} if sql else {}
        )
