"""
主应用入口
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import Base, local_engine, test_local_connection
from app.api.v1 import api_router
from app.api.v1 import auth, api_docs, interface_configs, interface_executor, database_configs, table_configs, interface_proxy, ai_models, terminologies, sql_examples, prompts, knowledge, chat, chat_schema, chat_recommendations, chat_export, dashboards

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)

# 创建logs目录（如果不存在）
logs_dir = BACKEND_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

logger.add(
    str(logs_dir / "app_{time:YYYY-MM-DD}.log"),
    rotation="00:00",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 创建FastAPI应用
app = FastAPI(
    title="MySQL表转服务API",
    description="将MySQL数据库表转换为RESTful API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理"""
    logger.warning("HTTP异常: {} - {}", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "detail": exc.detail if settings.DEBUG else "请联系管理员"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    logger.warning("请求验证失败: {}", exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数验证失败",
            "detail": exc.errors() if settings.DEBUG else "请求参数不正确"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error("未处理的异常: {}", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else "请联系管理员"
        }
    )


# 注册路由
# 注意：interface_proxy 必须最后注册，因为它使用通配符路径
app.include_router(auth.router)
app.include_router(database_configs.router)
app.include_router(table_configs.router)
app.include_router(api_docs.router)
app.include_router(interface_configs.router)
app.include_router(interface_executor.router)
# 智能问数功能API
app.include_router(ai_models.router)  # AI模型配置
app.include_router(terminologies.router)  # 术语库
app.include_router(sql_examples.router)  # SQL示例库
app.include_router(prompts.router)  # 自定义提示词
app.include_router(knowledge.router)  # 业务知识库
app.include_router(chat.router)  # 对话API
app.include_router(chat_schema.router)  # 对话Schema API
app.include_router(chat_recommendations.router)  # 对话推荐API
app.include_router(chat_export.router)  # 对话导出API
app.include_router(dashboards.router)  # 仪表板API
app.include_router(interface_proxy.router)  # 动态接口代理，必须最后注册

logger.info("路由注册完成")


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 50)
    logger.info("MySQL表转服务启动中...")
    logger.info("=" * 50)
    
    # 测试本地数据库连接
    if test_local_connection():
        logger.info("本地数据库连接成功")
        
        # 创建数据库表
        try:
            Base.metadata.create_all(bind=local_engine)
            logger.info("数据库表创建/检查完成")
        except Exception as e:
            logger.error("数据库表创建失败: {}", e)
    else:
        logger.error("本地数据库连接失败")
    
    logger.info("服务运行在: http://{}:{}", settings.HOST, settings.PORT)
    logger.info("=" * 50)


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "MySQL表转服务API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# 健康检查
@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "database": "connected" if test_local_connection() else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )

