from pydantic import BaseModel


class HealthResponse(BaseModel):
    """
    健康响应
    包含健康状态、服务名称
    """

    status: str
    service: str
