"""
AI模型配置路由
"""
import time
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
import time


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
    scene: Optional[str] = Field(None, description="使用场景（general/multimodal/code/math/agent/long_context/low_cost/enterprise/education/medical/legal/finance/government/industry/social/roleplay）")
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
    scene: Optional[str] = None
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
                "scene": model.scene,
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
                "scene": model.scene,
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
        # 验证提供商（扩展支持更多提供商）
        from app.core.llm.factory import LLMFactory
        supported_providers = LLMFactory.get_supported_providers()
        if config_data.provider.lower() not in supported_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的提供商: {config_data.provider}，支持的提供商: {supported_providers}"
            )
        
        # 验证场景值（如果提供）
        valid_scenes = ["general", "multimodal", "code", "math", "agent", "long_context", 
                       "low_cost", "enterprise", "education", "medical", "legal", 
                       "finance", "government", "industry", "social", "roleplay"]
        scene = config_data.scene if config_data.scene else "general"
        if scene not in valid_scenes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的场景值: {scene}，支持的场景: {valid_scenes}"
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
            scene=scene,
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
        if config_data.scene is not None:
            # 验证场景值
            valid_scenes = ["general", "multimodal", "code", "math", "agent", "long_context", 
                           "low_cost", "enterprise", "education", "medical", "legal", 
                           "finance", "government", "industry", "social", "roleplay"]
            if config_data.scene not in valid_scenes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的场景值: {config_data.scene}，支持的场景: {valid_scenes}"
                )
            update_data["scene"] = config_data.scene
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


@router.post("/{model_id}/test", response_model=ResponseModel)
async def test_model_connection(
    model_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_local_db)
):
    """测试AI模型连接"""
    from app.core.llm.factory import LLMFactory
    
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
                detail="模型未启用，无法测试"
            )
        
        # 创建客户端实例
        try:
            llm_client = LLMFactory.create_client(model)
        except Exception as e:
            logger.error(f"创建LLM客户端失败: {e}", exc_info=True)
            return ResponseModel(
                success=False,
                message="连接测试失败",
                data={
                    "success": False,
                    "error": f"创建客户端失败: {str(e)}",
                    "response_time": None
                }
            )
        
        # 发送测试消息
        test_message = "你好"
        start_time = time.time()
        
        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": test_message}],
                max_tokens=50  # 测试时使用较小的token数
            )
            
            response_time = time.time() - start_time
            
            # 检查响应
            if response and response.get("content"):
                return ResponseModel(
                    success=True,
                    message="连接测试成功",
                    data={
                        "success": True,
                        "response": response.get("content", "")[:100],  # 只返回前100字符
                        "response_time": round(response_time, 3),
                        "tokens_used": response.get("tokens_used"),
                        "model": response.get("model", model.model_name)
                    }
                )
            else:
                return ResponseModel(
                    success=False,
                    message="连接测试失败",
                    data={
                        "success": False,
                        "error": "响应内容为空",
                        "response_time": round(response_time, 3)
                    }
                )
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"测试模型连接失败: {e}", exc_info=True)
            return ResponseModel(
                success=False,
                message="连接测试失败",
                data={
                    "success": False,
                    "error": str(e),
                    "response_time": round(response_time, 3) if response_time > 0 else None
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试模型连接失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试模型连接失败: {str(e)}"
        )


@router.get("/providers/list", response_model=ResponseModel)
async def list_providers(
    current_user: User = Depends(get_current_active_user)
):
    """获取支持的AI模型提供商列表"""
    try:
        from app.core.llm.factory import LLMFactory
        
        providers = LLMFactory.get_supported_providers()
        
        # 提供商说明（扩展支持更多提供商）
        provider_info = {
            "deepseek": {
                "name": "DeepSeek",
                "description": "深度求索AI",
                "default_model": "deepseek-chat",
                "api_url": "https://api.deepseek.com",
                "api_key_url": "https://platform.deepseek.com/api_keys",
                "models": [
                    {"value": "deepseek-chat", "label": "DeepSeek Chat", "description": "通用对话模型"},
                    {"value": "deepseek-coder", "label": "DeepSeek Coder", "description": "代码生成模型"}
                ],
                "model_types": [
                    {"value": "llm", "label": "大语言模型"},
                    {"value": "code", "label": "代码模型"}
                ],
                "scenes": ["general", "code", "math"]
            },
            "qwen": {
                "name": "通义千问",
                "description": "阿里云通义千问",
                "default_model": "qwen-turbo",
                "api_url": "https://dashscope.aliyuncs.com",
                "api_key_url": "https://dashscope.console.aliyun.com/apiKey",
                "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
                "scenes": ["general", "code", "math", "agent", "long_context"]
            },
            "kimi": {
                "name": "Kimi",
                "description": "月之暗面Kimi",
                "default_model": "moonshot-v1-8k",
                "api_url": "https://api.moonshot.cn",
                "api_key_url": "https://platform.moonshot.cn/console/api-keys",
                "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
                "scenes": ["general", "long_context"]
            },
            "ernie": {
                "name": "百度文心",
                "description": "百度智能云千帆大模型平台",
                "default_model": "ERNIE-4.0-8K",
                "api_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                "api_key_url": "https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application",
                "models": ["ERNIE-4.0-8K", "ERNIE-4.0-8K-0205", "ERNIE-3.5-8K", "ERNIE-3.5-8K-0205"],
                "scenes": ["general", "multimodal", "enterprise"]
            },
            "hunyuan": {
                "name": "腾讯混元",
                "description": "腾讯云混元大模型",
                "default_model": "hunyuan-pro",
                "api_url": "https://hunyuan.tencentcloudapi.com",
                "api_key_url": "https://console.cloud.tencent.com/cam/capi",
                "models": ["hunyuan-pro", "hunyuan-standard", "hunyuan-lite"],
                "scenes": ["general", "multimodal"]
            },
            "doubao": {
                "name": "字节豆包",
                "description": "火山引擎豆包大模型",
                "default_model": "doubao-pro-4k",
                "api_url": "https://ark.cn-beijing.volces.com/api/v3",
                "api_key_url": "https://console.volcengine.com/ark/region:ark+cn-beijing/api",
                "models": ["doubao-pro-4k", "doubao-lite-4k", "doubao-pro-32k", "doubao-lite-32k"],
                "scenes": ["general", "low_cost"]
            },
            "pangu": {
                "name": "华为盘古",
                "description": "华为云ModelArts",
                "default_model": "pangu-sigma",
                "api_url": "https://modelarts.cn-north-4.myhuaweicloud.com/v1",
                "api_key_url": "https://console.huaweicloud.com/iam/#/mine/accessKey",
                "models": ["pangu-sigma", "pangu-alpha"],
                "scenes": ["enterprise", "government", "industry"]
            },
            "glm": {
                "name": "智谱GLM",
                "description": "智谱AI开放平台",
                "default_model": "GLM-4-Plus",
                "api_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key_url": "https://open.bigmodel.cn/usercenter/apikeys",
                "models": ["GLM-4-Plus", "GLM-4", "GLM-3-Turbo", "GLM-4-Air", "GLM-4-AirX"],
                "scenes": ["general", "code", "math", "agent"]
            },
            "sensetime": {
                "name": "商汤日日新",
                "description": "商汤科技开放平台",
                "default_model": "SenseNova-5.5",
                "api_url": "https://api.sensenova.cn/v1",
                "api_key_url": "https://platform.sensenova.cn/",
                "models": ["SenseNova-5.5", "SenseChat-5", "SenseChat-4"],
                "scenes": ["multimodal", "enterprise", "finance"]
            },
            "spark": {
                "name": "科大讯飞星火",
                "description": "讯飞开放平台",
                "default_model": "Spark-4.0-Ultra",
                "api_url": "https://spark-api.xf-yun.com/v1",
                "api_key_url": "https://www.xfyun.cn/console/createApi",
                "models": ["Spark-4.0-Ultra", "Spark-3.5-Max", "Spark-3.5-Pro", "Spark-3.1"],
                "scenes": ["education", "medical", "legal"]
            },
            "minimax": {
                "name": "MiniMax",
                "description": "MiniMax开放平台",
                "default_model": "abab6.5",
                "api_url": "https://api.minimax.chat/v1",
                "api_key_url": "https://platform.minimax.chat/",
                "models": ["abab6.5", "abab6", "abab5.5"],
                "scenes": ["social", "roleplay"]
            },
            "yi": {
                "name": "零一万物Yi",
                "description": "零一万物开放平台",
                "default_model": "yi-34b-chat",
                "api_url": "https://api.01.ai/v1",
                "api_key_url": "https://platform.01.ai/",
                "models": ["yi-34b-chat", "yi-6b-chat", "yi-34b-chat-200k"],
                "scenes": ["general"]
            },
            "skywork": {
                "name": "昆仑万维Skywork",
                "description": "昆仑万维开放平台",
                "default_model": "skywork-13b-chat",
                "api_url": "https://api.skywork.ai/v1",
                "api_key_url": "https://platform.skywork.ai/",
                "models": ["skywork-13b-chat", "skywork-6b-chat"],
                "scenes": ["general"]
            }
        }
        
        result = []
        for provider in providers:
            if provider in provider_info:
                result.append({
                    "provider": provider,
                    **provider_info[provider]
                })
            else:
                # 如果提供商不在info中，返回基本信息
                result.append({
                    "provider": provider,
                    "name": provider.upper(),
                    "description": f"{provider}大模型",
                    "default_model": "",
                    "api_url": "",
                    "scenes": ["general"]
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
