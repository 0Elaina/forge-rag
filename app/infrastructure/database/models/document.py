from datetime import datetime
from typing import Any
from uuid import UUID

# 导入SQLAlchemy的索引、整数、字符串、文本、大整数、外键类型
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

# 导入PostgreSQL的JSONB类型
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# 导入映射字段和映射列函数
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        文档模型
        用于表示应用中的文档，包含文档的基本信息、内容、元数据等
        UUIDPrimaryKeyMixin：继承自UUIDPrimaryKeyMixin，用于生成唯一标识文档的UUID主键
        TimestampMixin：继承自TimestampMixin，用于记录文档的创建时间和更新时间
        Base：继承自Base，用于继承基础模型的字段和方法
    """
    # 定义数据库表名
    __tablename__ = "documents"

    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # 定义外键，引用知识库的主键, ondelete="RESTRICT" 表示删除知识库时，不能删除引用它的文档
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        # 禁止为空
        nullable=False,
    )

    # 定义文件名字段，不允许为空
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # 定义文件扩展名字段，不允许为空
    file_ext: Mapped[str] = mapped_column(String(32), nullable=False)
    # MIME 类型（Multipurpose Internet Mail Extensions）
    # 标识文件格式，如 pdf → "application/pdf"、md → "text/markdown"
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 定义文件大小字段，不允许为空
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 定义文件路径字段，不允许为空
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    # 定义文件哈希值字段，允许为空
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # 定义文档状态字段，默认值为 "uploaded"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    # 定义解析错误信息字段，允许为空
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 定义分块数量字段，默认值为 0
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 定义嵌入模型字段，允许为空
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 定义处理开始时间字段，允许为空
    process_started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # 定义处理结束时间字段，允许为空
    process_finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # 定义元数据字段，允许为空
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    # 定义创建人字段，允许为空
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # 定义更新人字段，允许为空
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # 定义删除时间字段，允许为空
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        # 定义索引，用于快速查询文档所属的知识库
        Index("idx_doc_kb_id", "knowledge_base_id"),
        # 定义索引，用于快速查询文档状态
        Index("idx_doc_status", "status"),
        # 定义索引，用于快速查询文档的文件哈希值
        Index("idx_doc_file_hash", "file_hash"),
        # 定义索引，用于快速查询文档的创建时间
        Index("idx_doc_created_at", "created_at"),
    )