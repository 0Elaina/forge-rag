# =============================================================================
# 应用配置模块
# =============================================================================
# 本模块基于 pydantic-settings，从环境变量 / .env 文件加载运行时配置。
#
# 设计原则：
#   - 所有配置项都有合理的默认值，本地开发开箱即用（指向 localhost 服务）；
#   - 生产环境通过环境变量覆盖默认值，不修改代码；
#   - 敏感信息（密码、密钥）仅在环境变量或 .env 中设置，不硬编码；
#   - 配置集中管理，而不是散落在各个模块中。
#
# 使用方式：
#   from app.common.config import get_settings
#   settings = get_settings()       # 单例，全局只加载一次
# =============================================================================

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类 —— 继承 BaseSettings，自动从环境变量或 .env 文件读取。

    每个类属性对应一个配置项，通过 Field(validation_alias=...) 指定对应的
    环境变量名。例如 app_name 从 APP_NAME 环境变量读取。

    validation_alias 是 pydantic 的"验证阶段别名"机制：
    - 它告诉 pydantic 在解析输入数据（这里是环境变量）时，除了属性名本身，
      还接受哪个名称作为数据来源；
    - 这里用来桥接 Python 命名规范（snake_case）和环境变量命名规范（UPPER_CASE）；
    - 与之对应的是 serialization_alias（序列化时用的别名）和 alias（同时作用于
      验证和序列化），config 场景基本只用 validation_alias。

    优先级（从高到低）：
        1. 运行时环境变量（export APP_NAME=prod）
        2. .env 文件中的值
        3. Field(default=...) 定义的默认值
    """

    model_config = SettingsConfigDict(
        # 从项目根目录的 .env 文件加载
        env_file=".env",
        # .env 文件编码
        env_file_encoding="utf-8",
        # 环境变量中有未定义的键时静默忽略
        extra="ignore",
        # 环境变量名不区分大小写（APP_NAME 和 app_name 等价）
        case_sensitive=False,
    )

    # =========================================================================
    # 应用基础配置
    # =========================================================================
    app_name: str = Field(
        default="forgerag-api",
        validation_alias="APP_NAME",
    )
    """应用名称 —— 用于日志、监控中的服务标识。"""

    app_env: str = Field(
        default="dev",
        validation_alias="APP_ENV",
    )
    """运行环境（dev / staging / production）。

    不同环境下可能执行不同的初始化逻辑（如 dev 自动加载测试数据、
    production 开启更严格的 CORS、staging 连接到预发布数据库等）。"""

    app_host: str = Field(
        default="0.0.0.0",
        validation_alias="APP_HOST",
    )
    """HTTP 服务监听地址。

    - 0.0.0.0 ：监听所有网络接口（Docker 容器内必须用此值）
    - 127.0.0.1：仅本地可访问（开发调试时用）"""

    app_port: int = Field(
        default=8000,
        validation_alias="APP_PORT",
    )
    """HTTP 服务监听端口。"""

    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    """日志级别 —— 可选值：DEBUG / INFO / WARNING / ERROR / CRITICAL。

    生产环境建议设为 WARNING 以减少日志量；调障时临时设为 DEBUG。"""

    # =========================================================================
    # 关系型数据库（PostgreSQL）
    # =========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://forgerag:forgerag@localhost:5432/forgerag",
        validation_alias="DATABASE_URL",
    )
    """PostgreSQL 连接串（AsyncPG 驱动）。

    格式：postgresql+asyncpg://<用户>:<密码>@<主机>:<端口>/<数据库名>
    默认指向本地 Docker 启动的 PostgreSQL（用户/密码/数据库均为 forgerag）。
    生产环境通过 DATABASE_URL 环境变量覆盖。"""

    # =========================================================================
    # 向量数据库（Qdrant）
    # =========================================================================
    qdrant_url: str = Field(
        default="http://localhost:6333",
        validation_alias="QDRANT_URL",
    )
    """Qdrant 服务地址。

    本地 Docker 部署默认使用 http://localhost:6333；
    生产环境一般是 https://<集群域名>:6333。"""

    qdrant_collection: str = Field(
        default="forgerag_chunks",
        validation_alias="QDRANT_COLLECTION",
    )
    """Qdrant 集合名称 —— 存储文档切块（chunk）的向量与元数据。"""

    # =========================================================================
    # 文件上传
    # =========================================================================
    upload_dir: str = Field(
        default="storage/uploads",
        validation_alias="UPLOAD_DIR",
    )
    """上传文件的本地存储目录。

    生产环境建议挂载持久化存储（如 S3 挂载点、NFS 或 PVC），
    确保容器重启后文件不丢失。"""

    max_upload_size_mb: int = Field(
        default=20,
        validation_alias="MAX_UPLOAD_SIZE_MB",
    )
    """单次上传文件的大小上限（单位：MB）。"""

    # =========================================================================
    # LLM（大语言模型）配置
    # =========================================================================
    llm_provider: str = Field(
        default="openai_compatible",
        validation_alias="LLM_PROVIDER",
    )
    """LLM 提供者标识。

    当前仅支持 openai_compatible（兼容 OpenAI API 格式的服务均可），
    包括：OpenAI、Azure OpenAI、vLLM、Ollama（开启兼容模式时）等。

    后续可扩展为 anthropic / google / local 等。"""

    llm_api_base: str | None = Field(
        default=None,
        validation_alias="LLM_API_BASE",
    )
    """LLM API 的基础 URL。

    - OpenAI：https://api.openai.com/v1
    - 本地 vLLM：http://localhost:8000/v1
    - Azure：https://<资源名>.openai.azure.com

    设为 None 时由 langchain 的默认行为决定（通常指向 OpenAI 官方）。"""

    llm_api_key: str | None = Field(
        default=None,
        validation_alias="LLM_API_KEY",
    )
    """LLM API 密钥。

    敏感字段，仅通过环境变量或 .env 设置，不硬编码。
    设为 None 时调用方（langchain）会尝试从 OPENAI_API_KEY 等
    环境变量中读取。"""

    llm_model: str | None = Field(default=None, validation_alias="LLM_MODEL")
    """LLM 模型名称。

    设为 None 时，系统在第一次请求时自动从模型响应中推断模型名称。
    明确设置可跳过推断步骤，略微提升启动速度。"""

    # =========================================================================
    # Embedding（文本嵌入）模型配置
    # =========================================================================
    embedding_provider: str = Field(
        default="openai_compatible",
        validation_alias="EMBEDDING_PROVIDER",
    )
    """Embedding 模型提供者。

    与 llm_provider 类似，当前支持 openai_compatible 协议的服务。
    包括：OpenAI、Azure OpenAI、text-embeddings-inference（TEI）等。"""

    embedding_api_base: str | None = Field(
        default=None,
        validation_alias="EMBEDDING_API_BASE",
    )
    """Embedding API 基础 URL（格式同 llm_api_base）。"""

    embedding_api_key: str | None = Field(
        default=None,
        validation_alias="EMBEDDING_API_KEY",
    )
    """Embedding API 密钥（敏感字段，仅通过环境变量设置）。"""

    embedding_model: str = Field(
        default="text-embedding-ada-002",
        validation_alias="EMBEDDING_MODEL",
    )
    """Embedding 模型名称。

    默认使用 OpenAI 的 text-embedding-ada-002（1536 维）。
    若使用开源模型（如 BGE、gte 系列），需对应修改此值与
    EMBEDDING_API_BASE。"""

    embedding_dim: int | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_DIM", "EMBEDDING_MODEL_DIM"),
    )
    """Embedding 向量维度。

    设为 None 时，系统在第一次请求时自动从模型响应中推断维度。
    明确设置可跳过推断步骤，略微提升启动速度。"""

    # =========================================================================
    # Rerank（重排序）配置
    # =========================================================================
    rerank_enabled: bool = Field(
        default=False,
        validation_alias="RERANK_ENABLED",
    )
    """是否启用重排序阶段。

    启用后，检索返回 Top-K 候选块后，再经 rerank 模型重新打分排序，
    可显著提升最终结果的相关性，但会增加一次 API 调用延迟。"""

    rerank_provider: str | None = Field(
        default=None,
        validation_alias="RERANK_PROVIDER",
    )
    """Rerank 提供者（如 cohere / jina / openai_compatible）。

    设为 None 时取 llm_provider 的值。"""

    rerank_api_base: str | None = Field(
        default=None,
        validation_alias="RERANK_API_BASE",
    )
    """Rerank API 基础 URL。"""

    rerank_api_key: str | None = Field(
        default=None,
        validation_alias="RERANK_API_KEY",
    )
    """Rerank API 密钥（敏感字段，仅通过环境变量设置）。"""

    rerank_model: str = Field(
        default="text-rerank-ada-002",
        validation_alias="RERANK_MODEL",
    )
    """Rerank 模型名称。"""

    # =========================================================================
    # LLM 可观测性（Langfuse）
    # =========================================================================
    langfuse_enabled: bool = Field(
        default=False,
        validation_alias="LANGFUSE_ENABLED",
    )
    """是否启用 Langfuse Trace 追踪。

    Langfuse 是 LLM 应用的可观测性平台，记录每次 LLM 调用的
    输入/输出/延迟/成本。建议开发环境开启、生产环境选择性开启。
    默认关闭，需要使用时设置 LANGFUSE_ENABLED=true。"""

    langfuse_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
    )
    """Langfuse 服务地址。

    支持两个环境变量名（LANGFUSE_BASE_URL / LANGFUSE_HOST），
    以适应不同团队的命名习惯。"""

    langfuse_public_key: str | None = Field(
        default=None,
        validation_alias="LANGFUSE_PUBLIC_KEY",
    )
    """Langfuse 公钥（SDK 身份标识，非敏感）。"""

    langfuse_secret_key: str | None = Field(
        default=None,
        validation_alias="LANGFUSE_SECRET_KEY",
    )
    """Langfuse 密钥（敏感字段，用于 API 鉴权）。"""

    langfuse_environment: str | None = Field(
        default="dev",
        validation_alias="LANGFUSE_ENVIRONMENT",
    )
    """Langfuse 环境标签（用于在 Langfuse 仪表盘中区分不同环境的 Trace）。"""

    # =========================================================================
    # 可观测性采样率
    # =========================================================================
    observability_sample_rate: float = Field(
        default=1.0,
        validation_alias="OBSERVABILITY_SAMPLE_RATE",
    )
    """Trace 采样率，取值范围 [0.0, 1.0]。

    - 1.0：记录所有请求（开发 / 调障时使用）
    - 0.1：记录 10% 请求（高流量生产环境降低开销）
    - 0.0：完全关闭"""


@lru_cache
def get_settings() -> Settings:
    """获取全局 Settings 单例。

    使用 lru_cache 装饰器保证 Settings 只被实例化一次。
    重复调用直接返回缓存实例，避免反复读取 .env 文件。

    Returns:
        Settings: 应用配置单例
    """
    return Settings()
