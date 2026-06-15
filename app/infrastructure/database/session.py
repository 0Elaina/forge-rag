# 异步生成器类型，用于异步操作数据库会话
from collections.abc import AsyncGenerator

# 导入text函数，用于创建SQL文本语句
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    # 导入AsyncSession、async_sessionmaker、create_async_engine函数，用于异步操作数据库会话
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 导入get_settings函数，用于获取应用配置
from app.common.config import get_settings

# 获取应用配置
settings = get_settings()

# 创建异步数据库引擎
async_engine = create_async_engine(
    url=settings.database_url,
    # 开启连接池预连接，用于检查数据库连接是否有效
    pool_pre_ping=True,
    # 开启SQL语句日志，用于调试，使用开发环境时开启
    echo=settings.app_env == "dev",
)

# 创建异步数据库会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    # 使用AsyncSession类，用于异步操作数据库会话
    class_=AsyncSession,
    # 禁用会话过期，用于保持会话状态
    expire_on_commit=False,
    # 禁用自动刷新，用于手动刷新会话
    autoflush=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（FastAPI 依赖注入）
    ============================================================================
    用途:
        作为 FastAPI 的 Depends 依赖项使用, 为每个请求自动创建一个数据库会话,
        请求结束后自动关闭并归还连接到连接池。

    为何使用 yield 而不是 return:
        FastAPI 依赖项支持两种模式:
        - yield（生成器）: yield 之前的代码在请求进入时执行, yield 之后的代码
          在请求结束时执行 —— 这天然实现了「获取会话 → 处理请求 → 关闭会话」
          的生命周期管理, 等价于上下文管理器。
          即使请求处理过程中抛出异常, finally/except 块仍会执行, 确保会话被
          正确关闭, 不会泄露数据库连接。
        - return: 仅执行一次, 没有"清理"阶段, 需要调用方手动管理会话关闭。

    工作流程:
        ┌─────────────────────────────────────────────────────┐
        │  ① 请求到达 → FastAPI 调用 get_db_session()         │
        │  ② async with AsyncSessionLocal() as session       │
        │    └─ 从连接池中获取一个 AsyncSession 实例           │
        │  ③ yield session → 注入到路由处理函数的参数中         │
        │  ④ 路由处理函数使用 session 执行数据库操作             │
        │  ⑤ 请求处理完毕（或发生异常） → 回到此处继续执行       │
        │  ⑥ async with 块退出 → session 自动关闭并归还连接池   │
        └─────────────────────────────────────────────────────┘

    典型用法:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    类型说明:
        AsyncGenerator[AsyncSession, None]:
        - 第一个参数 AsyncSession: 生成器产出的值类型（yield 的值的类型）
        - 第二个参数 None: 生成器接收的值的类型（send() 传入的类型, 此处未使用）
    """
    async with AsyncSessionLocal() as session:
        # === 请求进入阶段 ===
        # AsyncSessionLocal() 是 async_sessionmaker 实例,
        # 调用它会从连接池中获取一个连接并包装为 AsyncSession。
        # async with 确保无论 yield 后的代码是否异常, 会话都会被关闭。
        # 对于 web 应用, 这意味着每个请求获得独立的数据库会话,
        # 请求间互不干扰, 同时连接得以复用（由连接池管理）。
        yield session
        # === 请求结束阶段 ===
        # FastAPI 在路由处理函数返回后（或抛出未捕获异常后）,
        # 会恢复生成器的执行, 使 async with 块退出。
        # 此时 session.__aexit__() 被调用:
        #   - 如果事务未提交, 自动回滚
        #   - 连接归还到连接池
        #   - 释放所有与 session 关联的资源
        # 这保证了即使开发者忘记手动关闭会话, 也不会发生连接泄露。

async def check_postgres_connection() -> bool:
    """
    检查 PostgreSQL 数据库连接是否正常（健康探针）
    ============================================================================
    用途:
        供健康检查端点调用, 验证数据库服务是否可达且响应正常。
        典型的"数据库存活探针 (liveness probe)"。

    为何执行 "SELECT 1" 而不是直接连接:
        - 建立 TCP 连接只表示数据库端口开放, 不代表数据库服务本身正常。
        - "SELECT 1" 是标准的数据库心跳检查 —— 如果数据库能够解析并执行
          一条最简单的 SQL 语句, 说明数据库引擎是活的、认证有效。
        - 几乎所有数据库驱动和 ORM 都采用此模式检查连接健康状态。

    异步上下文管理器:
        async with async_engine.connect() as connection:
        - create_async_engine 创建的引擎本身是连接池的管理者,
          .connect() 从池中借用一个连接, async with 块退出时归还。
        - 这与 get_db_session() 使用 AsyncSessionLocal 的区别:
          AsyncSessionLocal 是会话工厂（管理事务和工作单元）,
          .connect() 是原始连接（直接操作裸连接, 不经过 ORM 事务管理）。
        - 此处使用 .connect() 而非会话, 是因为检查连接不需要事务和 ORM,
          直接使用连接更轻量、开销更小。

    返回值:
        True  → 数据库连接正常, 可以继续处理请求
        False → 不会返回 False —— 如果连接或查询失败, 会抛出异常,
                由上层异常处理中间件捕获并返回 503 Service Unavailable。
    """
    async with async_engine.connect() as connection:
        # 从连接池中获取一个原始数据库连接
        await connection.execute(text("SELECT 1"))
        # 执行最简单的 SQL 查询 —— 只返回一个数字 1。
        # text("SELECT 1") 将普通字符串包装为 SQLAlchemy 可执行的
        # TextClause 对象。不需要 ORM 模型或 Table 对象。
        # 如果数据库正常, 该查询始终成功并返回 1。
        # 如果数据库不可用（宕机、网络中断、认证失败等）,
        # 此行会抛出异常（如 OperationalError）, 不会走到 return True。
        return True