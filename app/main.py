# 导入 FastAPI 框架核心类
from fastapi import FastAPI

# 导入 API 路由配置，包含所有 v1 版本的接口路由
from app.api.v1.router import api_router

# 导入应用配置获取函数，用于读取环境变量和配置信息
from app.common.config import get_settings


def create_app() -> FastAPI:
    """
    应用工厂函数，用于创建和配置 FastAPI 应用实例。

    Returns:
        FastAPI: 配置完成的 FastAPI 应用实例
    """
    # 获取应用配置（包括应用名称、数据库连接等）
    settings = get_settings()

    # 创建 FastAPI 应用实例，配置基本信息
    app = FastAPI(
        title=settings.app_name,  # 应用标题，从配置中读取
        version="0.1.0",  # API 版本号
        description="ForgeRAG 企业知识库代理 RAG 后端系统",  # API 描述信息
        docs_url="/docs",  # Swagger UI 文档路径
        redoc_url="/redoc",  # ReDoc 文档路径
        openapi_url="/openapi.json",  # OpenAPI 规范 JSON 文件路径
    )

    # 注册 API 路由，所有 v1 版本的接口都将使用 /api/v1 前缀
    # 例如：/api/v1/chat, /api/v1/documents 等
    app.include_router(api_router, prefix="/api/v1")

    return app


# 创建全局应用实例，供 ASGI 服务器（如 uvicorn）使用
app = create_app()
