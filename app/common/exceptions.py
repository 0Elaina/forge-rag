from enum import StrEnum


class ErrorCode(StrEnum):
    """错误码枚举"""
    OK = "OK" # 响应成功
    VALIDATION_ERROR = "VALIDATION_ERROR" # 请求参数校验失败
    BAD_REQUEST = "BAD_REQUEST" # 请求参数错误
    NOT_FOUND = "NOT_FOUND" # 资源不存在
    BUSINESS_ERROR = "BUSINESS_ERROR" # 业务逻辑错误
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR" # 外部服务错误
    DATABASE_ERROR = "DATABASE_ERROR" # 数据库错误
    VECTOR_STORE_ERROR = "VECTOR_STORE_ERROR" # 向量数据库错误
    MODEL_SERVICE_ERROR = "MODEL_SERVICE_ERROR" # 模型服务错误
    INTERNAL_ERROR = "INTERNAL_ERROR" # 内部错误
    
class AppException(Exception):
    """应用异常基类"""
    def __init__(
        self, # 异常实例
        message: str, # 异常消息
        code: ErrorCode = ErrorCode.INTERNAL_ERROR, # 错误码
        status_code: int = 500 # HTTP 状态码
    ) -> None:
        """初始化应用异常"""
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ParameterException(AppException):
    """请求参数校验失败异常"""
    def __init__(self, message: str = "validation error") -> None:
        """初始化请求参数校验失败异常"""
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 422)

class BusinessException(AppException):
    """业务逻辑错误异常"""
    def __init__(self, message: str = "business error") -> None:
        super().__init__(message, ErrorCode.BUSINESS_ERROR, 400)
        
        
class NotFoundException(AppException):
    """资源不存在异常"""
    def __init__(self, message: str = "resource not found") -> None:
        super().__init__(message, ErrorCode.NOT_FOUND, 404)


class ExternalServiceException(AppException):
    """外部服务错误异常"""
    def __init__(self, message: str = "external service error") -> None:
        super().__init__(message, ErrorCode.EXTERNAL_SERVICE_ERROR, 502)


class DatabaseException(AppException):
    """数据库错误异常"""
    def __init__(self, message: str = "database error") -> None:
        super().__init__(message, ErrorCode.DATABASE_ERROR, 500)


class VectorStoreException(AppException):
    """向量数据库错误异常"""
    def __init__(self, message: str = "vector store error") -> None:
        super().__init__(message, ErrorCode.VECTOR_STORE_ERROR, 502)


class ModelServiceException(AppException):
    """模型服务错误异常"""
    def __init__(self, message: str = "model service error") -> None:
        super().__init__(message, ErrorCode.MODEL_SERVICE_ERROR, 502)