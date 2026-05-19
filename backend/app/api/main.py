"""FastAPI 主应用

创建 FastAPI 应用实例，配置中间件和路由
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings, print_config, validate_config
from ..logging_config import LOGGING_CONFIG
from .routes import trip

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    # 在子进程中重新应用日志配置（reload 模式下 log_config 可能丢失）
    logging.config.dictConfig(LOGGING_CONFIG)

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="基于 LangGraph 的智能旅行规划助手 API",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置 CORS 中间件，允许前端跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # 注册路由
    app.include_router(trip.router, prefix="/api")

    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("=" * 60)
    logger.info("STARTING: %s v%s", get_settings().app_name, get_settings().app_version)
    logger.info("=" * 60)

    print_config()

    # 验证配置
    try:
        validate_config()
        logger.info("[SUCCESS] Configuration validated")
    except ValueError as e:
        logger.error("[ERROR] Configuration validation failed: %s", e)
        raise

    logger.info("[INFO] API Docs: http://localhost:8001/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    print("\n[INFO] Application is shutting down...")


@app.get("/", summary="根路径")
async def root():
    """根路径返回服务信息"""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """健康检查接口，用于监控和负载均衡探测"""
    return {"status": "healthy"}
