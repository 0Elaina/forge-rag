from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    API 响应模型
    用于统一 API 响应格式
    包含成功/失败状态、状态码、消息、数据、请求 ID、跟踪 ID
    """

    success: bool
    code: str
    message: str
    data: T | None = None
    request_id: str | None = None
    trace_id: str | None = None


def success_response(
    data: T | None = None,
    message: str = "success",
    request_id: str | None = None,
    trace_id: str | None = None,
) -> ApiResponse[T]:
    """
    成功响应
    包含成功状态、状态码、消息、数据、请求 ID、跟踪 ID
    """
    return ApiResponse(
        success=True,
        code="OK",
        message=message,
        data=data,
        request_id=request_id,
        trace_id=trace_id,
    )


def error_response(
    code: str, message: str, request_id: str | None = None, trace_id: str | None = None
) -> ApiResponse[T]:
    """
    失败响应
    包含失败状态、状态码、消息、请求 ID、跟踪 ID
    """
    return ApiResponse(
        success=False,
        code=code,
        message=message,
        data=None,
        request_id=request_id,
        trace_id=trace_id,
    )
