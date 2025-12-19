"""
初始化AI模型配置脚本
创建默认的DeepSeek模型配置
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import AIModelConfig
from app.core.password_encryption import encrypt_password
from loguru import logger


def init_default_ai_models():
    """初始化默认AI模型配置"""
    db = LocalSessionLocal()
    
    try:
        # DeepSeek配置（使用用户提供的API密钥）
        deepseek_api_key = "sk-1da6b990e30a4fa18349e7b6e9ce9b09"
        
        # 检查是否已存在DeepSeek配置
        existing_deepseek = db.query(AIModelConfig).filter(
            AIModelConfig.provider == "deepseek",
            AIModelConfig.model_name == "deepseek-chat"
        ).first()
        
        if not existing_deepseek:
            deepseek_config = AIModelConfig(
                name="DeepSeek Chat",
                provider="deepseek",
                api_key=encrypt_password(deepseek_api_key),
                api_base_url="https://api.deepseek.com",
                model_name="deepseek-chat",
                max_tokens=2000,
                temperature="0.7",
                is_default=True,  # 设为默认模型
                is_active=True
            )
            db.add(deepseek_config)
            logger.info("创建DeepSeek模型配置")
        else:
            # 更新现有配置的API密钥
            existing_deepseek.api_key = encrypt_password(deepseek_api_key)
            existing_deepseek.is_default = True
            existing_deepseek.is_active = True
            logger.info("更新DeepSeek模型配置")
        
        # 提交更改
        db.commit()
        logger.info("AI模型配置初始化完成")
        
        # 打印配置信息
        models = db.query(AIModelConfig).all()
        print("\n已配置的AI模型：")
        for model in models:
            print(f"  - {model.name} ({model.provider}) - {'默认' if model.is_default else ''} - {'启用' if model.is_active else '禁用'}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"初始化AI模型配置失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始初始化AI模型配置...")
    init_default_ai_models()
    print("初始化完成！")


