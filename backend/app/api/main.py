"""FastAPI 主应用

创建 FastAPI 应用实例，配置中间件和路由
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings, print_config, validate_config
from .routes import trip


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
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
    print("\n" + "=" * 60)
    print(f"STARTING: {get_settings().app_name} v{get_settings().app_version}")
    print("=" * 60)
    
    print_config()
    
    # 验证配置
    try:
        validate_config()
        print("\n[SUCCESS] Configuration validated")
    except ValueError as e:
        print(f"\n[ERROR] Configuration validation failed:\n{e}")
        raise
    
    print("\n[INFO] API Docs: http://localhost:8001/docs")
    print("=" * 60 + "\n")


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
