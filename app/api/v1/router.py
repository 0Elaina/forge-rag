from fastapi import APIRouter

from app.api.v1.endpoints import health

"""
    API 路由器
    包含所有 API 路由
"""
# 1. 实例化一个主路由对象
api_router = APIRouter()

# 2. 将子路由注册（挂载）到主路由上
api_router.include_router(health.router)
