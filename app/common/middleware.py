from collections.abc import Awaitable, Callable
from contextvars import ContextVar  # 上下文变量
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware  # 基础 HTTP 中间件
from starlette.requests import Request
from starlette.responses import Response

# 请求 ID 上下文变量, 仅限在请求处理过程中使用
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
# 跟踪 ID 上下文变量, 仅限在请求处理过程中使用
_trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)

def generate_request_id() -> str:
    """生成请求 ID"""
    return f"req_{uuid4().hex}" # uuid4().hex: 生成随机 UUID 4 字符串, 并转换为十六进制表示

def get_request_id() -> str | None:
    """获取当前请求 ID"""
    return _request_id_ctx.get()

def get_trace_id() -> str | None:
    """获取当前跟踪 ID"""
    return _trace_id_ctx.get()

def set_trace_id(trace_id: str | None) -> None:
    """设置当前跟踪 ID"""
    _trace_id_ctx.set(trace_id)
    
class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件 —— 为每个请求分配唯一标识, 并注入响应头

    职责:
        1. 从传入请求的 `X-Request-Id` 头中提取请求 ID（如果客户端提供了）
        2. 若客户端未提供, 则自动生成一个新的请求 ID
        3. 将请求 ID 写入当前上下文, 供后续处理链路（日志、追踪等）使用
        4. 将请求 ID 设置在响应头 `X-Request-Id` 中, 回传给客户端
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 优先复用客户端传入的请求 ID（用于分布式链路追踪的上下游串联）,
        # 若不存在则自动生成一个新的唯一 ID（格式: req_<32位hex>）
        request_id = request.headers.get("X-Request-Id") or generate_request_id()

        # 将请求 ID 写入 ContextVar, 使其在当前请求的处理链路中全局可访问;
        # 同时保存返回的 Token, 用于后续恢复上下文变量到之前的状态
        token = _request_id_ctx.set(request_id)

        try:
            # 将请求传递给下一个中间件或路由处理器, 等待响应
            response = await call_next(request)

            # 将请求 ID 注入响应头, 便于客户端或下游服务追踪请求
            response.headers["X-Request-Id"] = request_id
            return response

        finally:
            # 确保无论处理成功还是发生异常, 都重置 ContextVar,
            # 避免请求 ID 泄露到其他请求的上下文中（上下文变量跨请求污染）
            _request_id_ctx.reset(token)
