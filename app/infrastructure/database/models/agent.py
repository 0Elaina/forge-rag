from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        代理运行记录
        包含代理运行的详细信息, 包括关联的QA记录, 知识库, 状态, 响应延迟等
    """
    __tablename__ = "agent_runs"
    
    # 关联的QA记录ID，允许为空, 当关联的QA记录被删除时, 保持为NULL
    qa_record_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qa_records.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 关联的知识库ID, 不能为空, 当关联的知识库被删除时, 抛出异常
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    final_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    refuse_reason: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 最大迭代次数, 不能为空
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    # 实际迭代次数, 默认值为0
    actual_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # LangGraph流程版本, 允许为空
    graph_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 最终状态快照, 允许为空
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 响应延迟, 允许为空
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    __table_args__ = (
        # 关联的QA记录ID索引
        Index("idx_agent_run_qa_id", "qa_record_id"),
        # 关联的知识库ID索引
        Index("idx_agent_run_kb_id", "knowledge_base_id"),
        # 状态索引
        Index("idx_agent_run_status", "status"),
        # 跟踪ID索引
        Index("idx_agent_run_trace_id", "trace_id"),
    )
    
    
class AgentStep(UUIDPrimaryKeyMixin, Base):
    """
        代理运行步骤记录
        包含代理运行的详细步骤信息, 包括关联的代理运行, 步骤, 输入, 输出等
    """
    __tablename__ = "agent_steps"
    
    # 关联的代理运行ID, 不能为空, 当关联的代理运行被删除时, 级联删除关联的步骤记录
    agent_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False
    )
    
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 执行顺序, 不能为空
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 输入摘要, 允许为空
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # 输出摘要, 允许为空
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    # 决策结果, 允许为空
    decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Langfuse Span ID, 用于跟踪步骤的执行, 允许为空
    span_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    __table_args__ = (
        # 关联的代理运行ID索引
        Index("idx_agent_step_run_id", "agent_run_id"),
        # 执行顺序索引
        Index("idx_agent_step_order", "agent_run_id", "step_order"),
        # 步骤名称索引
        Index("idx_agent_step_name", "step_name"),
        # Langfuse Span ID索引
        Index("idx_agent_step_trace_span", "trace_id", "span_id")
    )
    
