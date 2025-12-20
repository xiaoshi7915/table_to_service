"""
权限控制模块
提供细粒度的权限检查功能
"""
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.models import User, DatabaseConfig, InterfaceConfig, ChatSession


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def check_database_access(
        db: Session,
        user: User,
        database_config_id: int,
        raise_exception: bool = True
    ) -> bool:
        """
        检查用户是否有权限访问指定的数据库配置
        
        Args:
            db: 数据库会话
            user: 当前用户
            database_config_id: 数据库配置ID
            raise_exception: 是否在无权限时抛出异常
            
        Returns:
            bool: 是否有权限
            
        Raises:
            HTTPException: 如果无权限且raise_exception=True
        """
        db_config = db.query(DatabaseConfig).filter(
            DatabaseConfig.id == database_config_id
        ).first()
        
        if not db_config:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="数据库配置不存在"
                )
            return False
        
        # 检查是否是配置的所有者
        if db_config.user_id != user.id:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问此数据库配置"
                )
            return False
        
        return True
    
    @staticmethod
    def check_interface_access(
        db: Session,
        user: User,
        interface_id: int,
        raise_exception: bool = True
    ) -> bool:
        """
        检查用户是否有权限访问指定的接口配置
        
        Args:
            db: 数据库会话
            user: 当前用户
            interface_id: 接口配置ID
            raise_exception: 是否在无权限时抛出异常
            
        Returns:
            bool: 是否有权限
            
        Raises:
            HTTPException: 如果无权限且raise_exception=True
        """
        interface = db.query(InterfaceConfig).filter(
            InterfaceConfig.id == interface_id
        ).first()
        
        if not interface:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="接口配置不存在"
                )
            return False
        
        # 检查是否是接口的所有者
        if interface.user_id != user.id:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问此接口配置"
                )
            return False
        
        return True
    
    @staticmethod
    def check_session_access(
        db: Session,
        user: User,
        session_id: int,
        raise_exception: bool = True
    ) -> bool:
        """
        检查用户是否有权限访问指定的对话会话
        
        Args:
            db: 数据库会话
            user: 当前用户
            session_id: 会话ID
            raise_exception: 是否在无权限时抛出异常
            
        Returns:
            bool: 是否有权限
            
        Raises:
            HTTPException: 如果无权限且raise_exception=True
        """
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()
        
        if not session:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="对话会话不存在"
                )
            return False
        
        # 检查是否是会话的所有者
        if session.user_id != user.id:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问此对话会话"
                )
            return False
        
        return True
    
    @staticmethod
    def check_resource_ownership(
        resource_user_id: int,
        current_user_id: int,
        resource_type: str = "资源",
        raise_exception: bool = True
    ) -> bool:
        """
        检查资源所有权
        
        Args:
            resource_user_id: 资源所有者的用户ID
            current_user_id: 当前用户ID
            resource_type: 资源类型（用于错误消息）
            raise_exception: 是否在无权限时抛出异常
            
        Returns:
            bool: 是否有权限
            
        Raises:
            HTTPException: 如果无权限且raise_exception=True
        """
        if resource_user_id != current_user_id:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"无权访问此{resource_type}"
                )
            return False
        
        return True
    
    @staticmethod
    def filter_user_resources(
        query,
        user_id: int,
        user_id_field_name: str = "user_id"
    ):
        """
        过滤查询，只返回属于指定用户的资源
        
        Args:
            query: SQLAlchemy查询对象
            user_id: 用户ID
            user_id_field_name: 用户ID字段名
            
        Returns:
            过滤后的查询对象
        """
        from sqlalchemy import inspect
        
        # 获取模型类
        model_class = query.column_descriptions[0]['entity'] if query.column_descriptions else None
        
        if model_class:
            # 检查模型是否有user_id字段
            mapper = inspect(model_class)
            if hasattr(mapper.columns, user_id_field_name):
                return query.filter(getattr(model_class, user_id_field_name) == user_id)
        
        # 如果无法自动过滤，返回原查询（需要调用者手动过滤）
        logger.warning(f"无法自动过滤资源，模型可能没有{user_id_field_name}字段")
        return query


def require_resource_owner(
    resource_user_id: int,
    current_user: User,
    resource_type: str = "资源"
):
    """
    装饰器：要求资源所有者权限
    
    Args:
        resource_user_id: 资源所有者的用户ID
        current_user: 当前用户
        resource_type: 资源类型
        
    Raises:
        HTTPException: 如果当前用户不是资源所有者
    """
    if resource_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"无权访问此{resource_type}，只有资源所有者可以执行此操作"
        )
