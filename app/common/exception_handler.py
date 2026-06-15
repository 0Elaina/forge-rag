from fastapi import FastAPI, Request

# 请求参数验证错误
from fastapi.exceptions import RequestValidationError

# JSON 响应
from starlette.responses import JSONResponse

from app.common.exceptions import AppException, ErrorCode
from app.common.response import error_response


def register_exception_handlers(app: FastAPI) -> None:
    """
        注册自定义异常处理函数
        @param app: FastAPI 应用实例
    """
    @app.exception_handler(AppException)
    async def app_exception_handler(
        # 传入request的原因: 用于获取请求ID和跟踪ID
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """
            自定义异常处理函数
            处理 AppException 类型的异常，返回 JSON 响应
            @param request: FastAPI 请求对象
            @param exc: AppException 异常实例
            @return: JSON 响应对象
        """
        body = error_response(
            code=exc.code.value,
            message=exc.message
        )
        return JSONResponse(
            status_code=exc.status_code,
            # model_dump(): 将模型实例转换为字典
            content=body.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
            自定义异常处理函数
            处理 RequestValidationError 类型的异常，返回 JSON 响应
            @param request: FastAPI 请求对象
            @param exc: RequestValidationError 异常实例
            @return: JSON 响应对象
        """
        body = error_response(
            code = ErrorCode.VALIDATION_ERROR.value,
            message = "request validation error"
        )
        return JSONResponse(
            # 422: Unprocessable Entity
            status_code=422,
            # model_dump(): 将模型实例转换为字典
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
            自定义异常处理函数
            处理未处理的异常，返回 JSON 响应
            @param request: FastAPI 请求对象
            @param exc: 未处理的异常实例
            @return: JSON 响应对象
        """
        body = error_response(
            code = ErrorCode.INTERNAL_ERROR.value,
            message = "internal server error"
        )
        return JSONResponse(
            status_code=500,
            content=body.model_dump()
        )