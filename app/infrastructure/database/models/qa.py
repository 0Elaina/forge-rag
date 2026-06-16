from typing import Any
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QARecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        问答记录模型
            用于存储问答记录的数据库表，包含问答记录的详细信息。
    """
    __tablename__ = "qa_records"
    
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        # 定义外键，关联 knowledge_bases 表的 id 字段，不允许为空, 限制删除操作
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    qa_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    
    refuse_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 定义 JSONB 字段，用于存储检索配置，允许为空
    retrieval_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rerank_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    model_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    # 定义字符串字段，用于存储提示版本，允许为空
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # 定义整数字段，用于存储请求的延迟时间（毫秒），允许为空
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    
    __table_args__ = (
        # 定义索引，用于快速查询知识库 ID 相关的记录
        Index("idx_qa_kb_id", "knowledge_base_id"),
        # 定义索引，用于快速查询状态相关的记录
        Index("idx_qa_status", "status"),
        # 定义索引，用于快速查询模式相关的记录
        Index("idx_qa_mode", "qa_mode"),
        # 定义索引，用于快速查询请求 ID 相关的记录
        Index("idx_qa_trace_id", "trace_id"),
        # 定义索引，用于快速查询创建时间相关的记录
        Index("idx_qa_created_at", "created_at")
    )
    
class QACitation(UUIDPrimaryKeyMixin, Base):
    """
        问答引用模型
            用于存储问答引用的数据库表，包含问答引用的详细信息。
    """
    __tablename__ = "qa_citations"
    
    qa_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qa_records.id", ondelete="CASCADE"),
        nullable=False
    )
    
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )
    
    chunk_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 定义文本字段，用于存储引用的文本，不允许为空
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # 定义浮点数字段，用于存储检索分数，允许为空
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 定义浮点数字段，用于存储重排分数，允许为空
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # 定义整数字段，用于存储引用顺序，不允许为空
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True
    )
    
    __table_args__ = (
        # 定义索引，用于快速查询 QA 记录 ID 相关的记录
        Index("idx_citation_qa_id", "qa_record_id"),
        # 定义索引，用于快速查询文档分块 ID 相关的记录
        Index("idx_citation_chunk_id", "chunk_id"),
        # 定义索引，用于快速查询文档 ID 相关的记录
        Index("idx_citation_doc_id", "document_id"),
        # 定义索引，用于快速查询引用顺序相关的记录
        Index("idx_citation_order", "qa_record_id", "citation_order")
    )