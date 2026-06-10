class ForgeRAGError(Exception):
    """
    ForgeRAG 错误基类
    用于统一处理 ForgeRAG 错误
    """

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        """
        初始化 ForgeRAG 错误
        包含错误消息、状态码
        """
        self.message = message
        self.code = code
        super().__init__(message)


class BusinessError(ForgeRAGError):
    """
    业务错误
    用于处理业务逻辑错误
    """


class ExternalError(ForgeRAGError):
    """
    外部错误
    用于处理外部系统错误
    """
