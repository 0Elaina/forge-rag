# 导入日期时间类型，用于定义创建时间和更新时间
from datetime import datetime

# 导入任意类型，用于定义模型字段的类型
from typing import Any

# 导入UUID类型，用于唯一标识知识库
from uuid import UUID

# 导入SQLAlchemy的索引、整数、字符串、文本类型
from sqlalchemy import Index, Integer, String, Text

# 导入PostgreSQL的JSONB类型
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# 导入SQLAlchemy的映射类型和映射列函数
from sqlalchemy.orm import Mapped, mapped_column

# 导入基础模型、时间戳混入、UUID主键混入
from app.infrastructure.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class KnowledgeBase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        知识库模型
        用于表示应用中的知识库，包含知识库的基本信息、文档数量、分块数量、元数据等
        UUIDPrimaryKeyMixin：继承自UUIDPrimaryKeyMixin，用于生成唯一标识知识库的UUID主键
        TimestampMixin：继承自TimestampMixin，用于记录知识库的创建时间和更新时间
        Base：继承自Base，用于继承基础模型的字段和方法
    """
    # 定义数据库表名
    __tablename__ = "knowledge_bases"

    # 定义知识库名称字段，不允许为空
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 定义知识库描述字段，允许为空
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 定义知识库状态字段，默认不允许为空，且值为"active"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    # 定义知识库所有者ID字段，允许为空, as_uuid=True 表示将UUID类型转换为Python UUID对象
    owner_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # 定义知识库文档数量字段，默认值为0
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 定义知识库分块数量字段，默认值为0
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 定义知识库元数据字段，存储任意 JSON 格式的附加信息
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        # PostgreSQL 的 JSONB 类型，支持二进制 JSON 存储、索引及高效字段查询
        JSONB,
        # 允许该列在数据库中为 NULL，对应 Python 类型中的 | None
        nullable=True,
    )

    # 定义知识库创建人ID字段，允许为空, as_uuid=True 表示将UUID类型转换为Python UUID对象
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # 定义知识库更新人ID字段，允许为空, as_uuid=True 表示将UUID类型转换为Python UUID对象
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # 定义知识库删除时间字段，允许为空, 数据类型由sqlalchemy自动处理
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # 定义数据库表索引
    __table_args__ = (
        # 定义索引，用于快速查询知识库状态
        Index("idx_kb_status", "status"),
        # 定义索引，用于快速查询知识库创建时间
        Index("idx_kb_create_at", "created_at"),
        Index(
            "idx_kb_name_active",
            "name",
            # 设置唯一索引，确保知识库名称在活动状态下是唯一的
            unique=True,
            # 仅索引未删除的知识库
            postgresql_where=deleted_at.is_(None),
        ),
    )