# 导入UTC和datetime模块
from datetime import UTC, datetime

# 导入UUID模块和uuid4函数
from uuid import UUID, uuid4

# 导入DateTime类型
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import (
    # 导入PG_UUID类型，用于PostgreSQL数据库的UUID类型
    UUID as PG_UUID,
)
from sqlalchemy.orm import (
    # 导入DeclarativeBase、Mapped、mapped_column函数，用于声明数据库模型
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基础模型"""
    
class UUIDPrimaryKeyMixin:
    """UUID 主键混入类"""
    
    id: Mapped[UUID] = mapped_column(
        # PG_UUID类型，用于PostgreSQL数据库的UUID类型，as_uuid=True表示将UUID转换为Python的UUID对象
        PG_UUID(as_uuid=True),
        # 主键，用于唯一标识数据库中的行
        primary_key=True,
        # 默认值为uuid4函数，用于生成新的UUID
        default=uuid4,
    )
    
class TimestampMixin:
    """时间戳混入类"""
    
    # 创建时间字段
    created_at: Mapped[datetime] = mapped_column(
        # DateTime类型，用于存储时间戳，timezone=True表示支持时区
        DateTime(timezone=True),
        # 默认值为当前时间，用于创建时间
        default=lambda: datetime.now(UTC),
        # 不允许为空，用于创建时间
        nullable=False,
    )

    # 更新时间字段
    updated_at: Mapped[datetime] = mapped_column(
        # DateTime类型，用于存储时间戳，timezone=True表示支持时区
        DateTime(timezone=True),
        # 默认值为当前时间，用于更新时间
        default=lambda: datetime.now(UTC),
        # 更新时间字段，用于更新时间
        onupdate=lambda: datetime.now(UTC),
        # 不允许为空，用于更新时间
        nullable=False,
    )