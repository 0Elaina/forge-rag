from pydantic import BaseModel


class HealthResponse(BaseModel):
    """
    健康响应
    包含健康状态、服务名称
    """

    status: str
    service: str

class ReadinessResponse(BaseModel):
    """
    就绪响应
    包含就绪状态、依赖状态
    """

    status: str
    dependencies: dict[str, str]