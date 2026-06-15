from fastapi.testclient import TestClient


def test_health_api(client: TestClient) -> None:
    """
    测试健康状态 API
    """
    response = client.get("/api/v1/health")

    # 测试健康状态响应状态码
    assert response.status_code == 200

    body = response.json()
    # 断言: 响应体包含 success 字段，且为 True
    assert body["success"] is True
    # 断言: 响应体包含 code 字段，且为 OK
    assert body["code"] == "OK"
    # 断言: 响应体包含 message 字段，且为 success
    assert body["message"] == "success"
    assert body["data"] == {
        # 断言: 响应体包含 data 字段，且包含 status 字段，且为 OK
        "status": "OK",
        # 断言: 响应体包含 data 字段，且包含 service 字段，且为 forgerag-api
        "service": "forgerag-api",
    }
    # 断言: 响应体包含 request_id 字段，且不为 None
    assert body["request_id"] is not None
    # 断言: 响应体包含 trace_id 字段，且为 None
    assert body["trace_id"] is None


def test_health_api_uses_client_request_id(client: TestClient) -> None:
    """
        测试健康状态 API 是否使用客户端请求 ID
    """
    # 发送 GET 请求，包含 X-Request-Id 头
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-Id": "req_client_test"},
    )

    # 解析 JSON 响应体
    body = response.json()
    # 断言: 响应体包含 request_id 字段，且为 req_client_test
    assert body["request_id"] == "req_client_test"
    # 断言: 响应头包含 X-Request-Id 字段，且为 req_client_test
    assert response.headers["X-Request-Id"] == "req_client_test"
