from app.common.exceptions import ErrorCode
from app.common.response import error_response, success_response


def test_success_response() -> None:
    """
        测试成功响应
        检查成功响应是否包含预期的字段
        包含 success, code, message, data, request_id, trace_id
    """
    
    response = success_response(data={"name": "ForgeRAG"}) # 创建成功响应
    
    assert response.success is True # 断言: 成功响应
    assert response.code == ErrorCode.OK.value # 断言: 状态码为 OK
    assert response.message == "success" # 断言: 消息为 success
    assert response.data == {"name": "ForgeRAG"} # 断言: 数据为 {"name": "ForgeRAG"}
    
def test_error_response() -> None:
    """
        测试失败响应
        检查失败响应是否包含预期的字段
        包含 success, code, message, request_id, trace_id
    """
    
    response = error_response(
        code=ErrorCode.BAD_REQUEST.value,
        message="bad request",
        request_id="req_test"
    )
    
    assert response.success is False # 断言: 失败响应
    assert response.code == ErrorCode.BAD_REQUEST.value # 断言: 状态码为 BAD_REQUEST
    assert response.message == "bad request" # 断言: 消息为 bad request
    assert response.data is None # 断言: 数据为 None
    assert response.request_id == "req_test" # 断言: 请求 ID为 req_test