from app.common.exceptions import (
    DatabaseException,
    ErrorCode,
    ModelServiceException,
    NotFoundException,
    ParameterException,
    VectorStoreException,
)


def test_parameter_exception() -> None:
    """
        测试参数异常
        检查参数异常是否包含预期的字段
        包含 code, status_code, message
    """
    # 创建参数异常
    exc = ParameterException("invalid parameter")

    # 断言: 状态码为 VALIDATION_ERROR
    assert exc.code == ErrorCode.VALIDATION_ERROR
    # 断言: 状态码为 422
    assert exc.status_code == 422
    # 断言: 消息为 invalid parameter
    assert exc.message == "invalid parameter"


def test_not_found_exception() -> None:
    """
        测试未找到异常
        检查未找到异常是否包含预期的字段
        包含 code, status_code, message
    """
    exc = NotFoundException("resource not found")

    # 断言: 状态码为 NOT_FOUND
    assert exc.code == ErrorCode.NOT_FOUND
    # 断言: 状态码为 404
    assert exc.status_code == 404
    # 断言: 消息为 resource not found
    assert exc.message == "resource not found"


def test_external_like_exceptions() -> None:
    """
        测试外部异常
        检查外部异常是否包含预期的字段
        包含 code, status_code, message
    """
    # 断言: 状态码为 DATABASE_ERROR
    assert DatabaseException().code == ErrorCode.DATABASE_ERROR
    # 断言: 状态码为 VECTOR_STORE_ERROR
    assert VectorStoreException().code == ErrorCode.VECTOR_STORE_ERROR
    # 断言: 状态码为 MODEL_SERVICE_ERROR
    assert ModelServiceException().code == ErrorCode.MODEL_SERVICE_ERROR
