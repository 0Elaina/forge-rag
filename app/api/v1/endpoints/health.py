from fastapi import APIRouter

from app.common.config import get_settings
from app.common.exceptions import ErrorCode
from app.common.response import ApiResponse, success_response
from app.schemas.system import HealthResponse

router = APIRouter(tags=["System"])


# 注册健康检查路由 —— GET /health
# response_model 显式声明响应结构为 ApiResponse[HealthResponse],
# 使 FastAPI 自动生成 OpenAPI 文档并校验响应数据
@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="检查系统健康状态",
)
async def health_check() -> ApiResponse[HealthResponse]:
    """健康检查端点

    用于 Kubernetes 等容器编排工具的存活探针 (liveness probe)
    和就绪探针 (readiness probe), 判断服务是否正常运行。

    Returns:
        标准 API 响应, 包含:
        - status: 错误码 (此处固定返回 SUCCESS, 表示服务健康)
        - service: 当前服务的名称 (从配置读取)
    """
    # 从全局配置中获取应用设置, 包括 app_name 等
    settings = get_settings()

    # 返回统一成功响应, 内嵌 HealthResponse 数据体
    return success_response(
        data=HealthResponse(
            # 固定返回 SUCCESS 错误码, 表示服务健康
            status=ErrorCode.OK,
            # 从配置读取服务名称, 用于多服务部署时区分不同服务
            service=settings.app_name,
        )
    )
