from fastapi.testclient import TestClient


def test_health_api(client: TestClient) -> None:
    """
    测试健康状态 API
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200  # 测试健康状态响应状态码
    assert response.json() == {
        "status": "ok",
        "service": "forgerag-api",
    }  # 测试健康状态响应 JSON 内容


def test_docs_page_available(client: TestClient) -> None:
    """
    测试文档页面是否可用
    """
    response = client.get("/docs")

    assert response.status_code == 200  # 测试文档页面响应状态码
    assert "text/html" in response.headers["content-type"]  # 测试文档页面响应内容类型
