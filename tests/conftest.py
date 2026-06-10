import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """
    创建测试客户端
    用于测试 API 路由
    """
    app = create_app()
    return TestClient(app)
