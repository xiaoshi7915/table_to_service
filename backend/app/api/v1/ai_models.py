"""
AI模型配置路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_local_db
from app.models import User, AIModelConfig
from app.schemas import ResponseModel
from app.core.security import get_current_active_user
from app.core.password_encryption import encrypt_password, decrypt_password
from loguru import logger


router = APIRouter(prefix="/api/v1/ai-models", tags=["AI模型配置"])


# ==================== 请求/响应模型 ====================

class AIModelConfigCreate(BaseModel):
    """创建AI模型配置请求模型"""
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商（deepseek, qwen, kimi等）")
    api_key: str = Field(..., description="API密钥")
    api_base_url: Optional[str] = Field(None, description="API基础URL")
    model_name: str = Field(..., description="具体模型名称")
    max_tokens: int = Field(2000, description="最大token数")
    temperature: str = Field("0.7", description="温度参数")
    is_default: bool = Field(False, description="是否设为默认模型")


class AIModelConfigUpdate(BaseModel):
    """更新AI模型配置请求模型"""
    name: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


# ==================== API路由 ====================

@router.get("", response_model=ResponseModel)
@router.get("/", response_model=ResponseModel)
async def list_ai_models(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取AI模型配置列表"""
    try:
        models = db.query(AIModelConfig).order_by(
            AIModelConfig.is_default.desc(),
            AIModelConfig.created_at.desc()
        ).all()
        
        result = []
        for model in models:
            # API密钥不返回，只返回是否已配置
            result.append({
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "api_base_url": model.api_base_url,
                "model_name": model.model_name,
                "max_tokens": model.max_tokens,
                "temperature": model.temperature,
                "is_default": model.is_default,
                "is_active": model.is_active,
                "has_api_key": bool(model.api_key),  # 只返回是否配置了密钥
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except Exception as e:
        logger.error(f"获取AI模型列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取AI模型列表失败: {str(e)}"
        )


@router.get("/{model_id}", response_model=ResponseModel)
async def get_ai_model(
    model_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """获取AI模型配置详情"""
    try:
        model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI模型配置不存在"
            )
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data={
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "api_base_url": model.api_base_url,
                "model_name": model.model_name,
                "max_tokens": model.max_tokens,
                "temperature": model.temperature,
                "is_default": model.is_default,
                "is_active": model.is_active,
                "has_api_key": bool(model.api_key),
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI模型详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取AI模型详情失败: {str(e)}"
        )


@router.post("", response_model=ResponseModel)
@router.post("/", response_model=ResponseModel)
async def create_ai_model(
    config_data: AIModelConfigCreate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """创建AI模型配置"""
    try:
        # 验证提供商
        supported_providers = ["deepseek", "qwen", "kimi"]
        if config_data.provider.lower() not in supported_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的提供商: {config_data.provider}，支持的提供商: {supported_providers}"
            )
        
        # 如果设置为默认模型，先取消其他默认模型
        if config_data.is_default:
            db.query(AIModelConfig).filter(AIModelConfig.is_default == True).update({"is_default": False})
        
        # 加密API密钥
        encrypted_api_key = encrypt_password(config_data.api_key)
        
        # 创建模型配置
        model_config = AIModelConfig(
            name=config_data.name,
            provider=config_data.provider.lower(),
            api_key=encrypted_api_key,
            api_base_url=config_data.api_base_url,
            model_name=config_data.model_name,
            max_tokens=config_data.max_tokens,
            temperature=config_data.temperature,
            is_default=config_data.is_default,
            is_active=True
        )
        
        db.add(model_config)
        db.commit()
        db.refresh(model_config)
        
        logger.info(f"用户 {current_user.username} 创建AI模型配置: {model_config.name}")
        
        return ResponseModel(
            success=True,
            message="创建成功",
            data={
                "id": model_config.id,
                "name": model_config.name,
                "provider": model_config.provider,
                "model_name": model_config.model_name,
                "is_default": model_config.is_default
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建AI模型配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建AI模型配置失败: {str(e)}"
        )


@router.put("/{model_id}", response_model=ResponseModel)
async def update_ai_model(
    model_id: int,
    config_data: AIModelConfigUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """更新AI模型配置"""
    try:
        model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI模型配置不存在"
            )
        
        # 更新字段
        update_data = {}
        if config_data.name is not None:
            update_data["name"] = config_data.name
        if config_data.provider is not None:
            update_data["provider"] = config_data.provider.lower()
        if config_data.api_key is not None:
            update_data["api_key"] = encrypt_password(config_data.api_key)
        if config_data.api_base_url is not None:
            update_data["api_base_url"] = config_data.api_base_url
        if config_data.model_name is not None:
            update_data["model_name"] = config_data.model_name
        if config_data.max_tokens is not None:
            update_data["max_tokens"] = config_data.max_tokens
        if config_data.temperature is not None:
            update_data["temperature"] = config_data.temperature
        if config_data.is_active is not None:
            update_data["is_active"] = config_data.is_active
        
        # 如果设置为默认模型，先取消其他默认模型
        if config_data.is_default is not None:
            if config_data.is_default:
                db.query(AIModelConfig).filter(
                    AIModelConfig.id != model_id,
                    AIModelConfig.is_default == True
                ).update({"is_default": False})
            update_data["is_default"] = config_data.is_default
        
        # 执行更新
        db.query(AIModelConfig).filter(AIModelConfig.id == model_id).update(update_data)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 更新AI模型配置: {model.name}")
        
        return ResponseModel(
            success=True,
            message="更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新AI模型配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新AI模型配置失败: {str(e)}"
        )


@router.delete("/{model_id}", response_model=ResponseModel)
async def delete_ai_model(
    model_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """删除AI模型配置"""
    try:
        model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI模型配置不存在"
            )
        
        # 如果是默认模型，不允许删除
        if model.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除默认模型，请先设置其他模型为默认"
            )
        
        db.delete(model)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除AI模型配置: {model.name}")
        
        return ResponseModel(
            success=True,
            message="删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除AI模型配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除AI模型配置失败: {str(e)}"
        )


@router.post("/{model_id}/set-default", response_model=ResponseModel)
async def set_default_model(
    model_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """设置默认AI模型"""
    try:
        model = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI模型配置不存在"
            )
        
        if not model.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将未启用的模型设为默认"
            )
        
        # 取消其他默认模型
        db.query(AIModelConfig).filter(AIModelConfig.id != model_id).update({"is_default": False})
        
        # 设置当前模型为默认
        model.is_default = True
        db.commit()
        
        logger.info(f"用户 {current_user.username} 设置默认AI模型: {model.name}")
        
        return ResponseModel(
            success=True,
            message="设置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"设置默认AI模型失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置默认AI模型失败: {str(e)}"
        )


@router.get("/providers/list", response_model=ResponseModel)
async def list_providers(
    current_user: User = Depends(get_current_active_user)
):
    """获取支持的AI模型提供商列表"""
    try:
        from app.core.llm.factory import LLMFactory
        
        providers = LLMFactory.get_supported_providers()
        
        # 提供商说明
        provider_info = {
            "deepseek": {
                "name": "DeepSeek",
                "description": "深度求索AI",
                "default_model": "deepseek-chat",
                "api_url": "https://api.deepseek.com"
            },
            "qwen": {
                "name": "通义千问",
                "description": "阿里云通义千问",
                "default_model": "qwen-turbo",
                "api_url": "https://dashscope.aliyuncs.com"
            },
            "kimi": {
                "name": "Kimi",
                "description": "月之暗面Kimi",
                "default_model": "moonshot-v1-8k",
                "api_url": "https://api.moonshot.cn"
            }
        }
        
        result = []
        for provider in providers:
            if provider in provider_info:
                result.append({
                    "provider": provider,
                    **provider_info[provider]
                })
        
        return ResponseModel(
            success=True,
            message="获取成功",
            data=result
        )
    except Exception as e:
        logger.error(f"获取提供商列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取提供商列表失败: {str(e)}"
        )


