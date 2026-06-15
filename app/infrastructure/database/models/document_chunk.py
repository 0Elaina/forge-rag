from typing import Any
from uuid import UUID

# 导入SQLAlchemy的索引、整数、字符串、文本、外键、唯一约束类型
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

# 导入PostgreSQL的JSONB类型
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# 导入映射字段和映射列函数
from sqlalchemy.orm import Mapped, mapped_column

# 导入基础模型、UUID主键混入、时间混入
from app.infrastructure.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    文档分块模型
    用于表示应用中的文档分块，包含文档分块的基本信息、内容、元数据等
    UUIDPrimaryKeyMixin：继承自UUIDPrimaryKeyMixin，用于生成唯一标识文档分块的UUID主键
    TimestampMixin：继承自TimestampMixin，用于记录文档分块的创建时间和更新时间
    Base：继承自Base，用于继承基础模型的字段和方法
    """

    # 定义数据库表名
    __tablename__ = "document_chunks"

    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # 定义外键，引用知识库表的ID字段，删除知识库时级联删除文档分块
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        # 禁止为空
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # 定义外键，引用文档表的ID字段，删除文档时级联删除文档分块
        ForeignKey("documents.id", ondelete="CASCADE"),
        # 禁止为空
        nullable=False,
    )

    # 定义整数字段，用于存储文档分块的索引，不允许为空
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 定义文本字段，用于存储文档分块的内容，不允许为空
    cotent: Mapped[str] = mapped_column(Text, nullable=False)
    # 定义字符串字段，用于存储文档分块的内容哈希值，允许为空
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # 定义整数字段，用于存储文档分块的token数量，允许为空
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 定义整数字段，用于存储文档分块的字符数量，允许为空
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 定义整数字段，用于存储文档分块的页码，允许为空
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 定义字符串字段，用于存储文档分块的章节标题，允许为空
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 定义整数字段，用于存储文档分块的起始偏移量，允许为空
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 定义整数字段，用于存储文档分块的结束偏移量，允许为空
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 定义字符串字段，用于存储文档分块的分块器名称，允许为空
    splitter_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 定义JSONB字段，用于存储文档分块的分块器配置，允许为空
    splitter_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # 定义字符串字段，用于存储文档分块的嵌入状态，允许为空，默认值为"pending"
    embedding_status: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default="pending"
    )
    # 定义字符串字段，用于存储文档分块的嵌入模型，允许为空
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 定义整数字段，用于存储文档分块的嵌入维度，允许为空
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 定义字符串字段，用于存储文档分块的Qdrant集合名称，允许为空
    qdrant_collection: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 定义字符串字段，用于存储文档分块的Qdrant点ID，允许为空
    qdrant_point_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 定义JSONB字段，用于存储文档分块的元数据，允许为空
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    __table_args__ = (
        # 定义索引，用于快速查询文档分块的知识库ID
        Index("idx_chunk_kb_id", "knowledge_base_id"),
        # 定义索引，用于快速查询文档分块的文档ID
        Index("idx_chunk_doc_id", "document_id"),
        # 定义索引，用于快速查询文档分块的Qdrant点ID
        Index("idx_chunk_qdrant_point_id", "qdrant_point_id"),
        # 定义索引，用于快速查询文档分块的嵌入状态
        Index("idx_chunk_embedding_status", "embedding_status"),
        # 定义唯一约束，确保文档分块的文档ID和索引是唯一的
        UniqueConstraint("document_id", "chunk_index", name="uk_chunk_doc_index"),
    )
