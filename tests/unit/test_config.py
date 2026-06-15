from app.common.config import get_settings


def test_settings_load_default_values() -> None:
    """
    测试配置加载默认配置
    """
    settings = get_settings()

    # 默认应用名称
    assert settings.app_name == "forgerag-api"
    # 默认环境环境变量
    assert settings.app_env in {"dev", "test", "prod"}
    # 默认应用端口
    assert settings.app_port == 8000
    # 默认 Qdrant 集合名称
    assert settings.qdrant_collection == "forgerag_chunks"
