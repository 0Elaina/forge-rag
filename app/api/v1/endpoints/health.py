from fastapi import APIRouter
from app.common.config import get_settings
from app.schemas.system import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="检查系统健康状态")
async def health_check() -> HealthResponse:
    """
    检查系统健康状态
    返回健康状态、服务名称
    """
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name)
