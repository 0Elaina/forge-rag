from fastapi.testclient import TestClient


def test_health_api(client: TestClient) -> None:
    """
    测试健康状态 API
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200  # 测试健康状态响应状态码
    
    body = response.json()
    assert body["success"] is True # 断言: 响应体包含 success 字段，且为 True
    assert body["code"] == "OK" # 断言: 响应体包含 code 字段，且为 OK
    assert body["message"] == "success" # 断言: 响应体包含 message 字段，且为 success
    assert body["data"] == {
        "status": "OK", # 断言: 响应体包含 data 字段，且包含 status 字段，且为 OK
        "service": "forgerag-api" # 断言: 响应体包含 data 字段，且包含 service 字段，且为 forgerag-api
    }
    assert body["request_id"] is not None # 断言: 响应体包含 request_id 字段，且不为 None
    assert body["trace_id"] is None # 断言: 响应体包含 trace_id 字段，且为 None


def test_health_api_uses_client_request_id(client: TestClient) -> None:
    """
        测试健康状态 API 是否使用客户端请求 ID
    """
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-Id": "req_client_test"},
    ) # 发送 GET 请求，包含 X-Request-Id 头


    body = response.json() # 解析 JSON 响应体
    assert body["request_id"] == "req_client_test" # 断言: 响应体包含 request_id 字段，且为 req_client_test
    assert response.headers["X-Request-Id"] == "req_client_test" # 断言: 响应头包含 X-Request-Id 字段，且为 req_client_test
