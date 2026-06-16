from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EvaluationDataset(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    """
        评估数据集模型
        包含数据集的基本信息, 如关联的知识库ID、名称、描述、状态、样本数量、元数据等
    """
    __tablename__ = "evaluation_datasets"
    
    # 关联的知识库ID, 允许为空, 删除时设置为NULL
    knowledge_base_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    
    # 样本数量, 默认值为0
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True
    )
    
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    __table_args__ = (
        Index("idx_eval_dataset_kb_id", "knowledge_base_id"),
        Index("idx_eval_dataset_status", "status"),
        Index("idx_eval_dataset_created_at", "created_at")
    )
    
class EvaluationSample(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        评估样本模型
        包含样本的基本信息, 如关联的数据集ID、评测问题、参考答案、
        期望命中文档ID列表、期望命中文档块ID列表、标签、难度、元数据等
    """
    __tablename__ = "evaluation_samples"
    
    # 关联的数据集ID, 删除时级联删除
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 评测问题, 不能为空
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # 参考答案
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 期望命中文档ID列表, 允许为空
    expected_document_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    expected_chunk_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True
    )
    
    __table_args__ = (
        Index("idx_eval_sample_dataset_id", "dataset_id"),
        Index("idx_eval_sample_difficulty", "difficulty"),
        Index("idx_eval_sample_created_at", "created_at")
    )
    
class EvaluationTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_tasks"
    
    # 关联的数据集ID, 删除时抛出异常, 不能为空
    dataset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # 关联的知识库ID, 删除时抛出异常, 不能为空
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # basic_rag or agentic_rag
    qa_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    # 评测任务状态, 默认值为pending
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    
    # 检索配置, 允许为空
    retrieval_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # 重排序配置, 允许为空
    rerank_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # 模型配置, 允许为空
    model_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    # 提示词版本, 允许为空
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # 样本总数, 默认值为0
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # 平均分数, 允许为空
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 开始时间, 允许为空
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True
    )
    
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    __table_args__ = (
        Index("idx_eval_task_dataset_id", "dataset_id"),
        Index("idx_eval_task_kb_id", "knowledge_base_id"),
        Index("idx_eval_task_status", "status"),
        Index("idx_eval_task_created_at", "created_at"),
        Index("idx_eval_task_trace_id", "trace_id")
    )
    
class EvaluationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
        评测结果模型
        包含每个评测样本的评测结果，包括问题、生成答案、参考答案、检索结果摘要、引用结果摘要、检索相关性得分、回答质量得分、引用质量得分、实证度得分
    """
    __tablename__ = "evaluation_results"
    
    # 关联的评测任务ID, 删除时级联删除
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_tasks.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 关联的评测样本ID, 删除时抛出异常, 不能为空
    sample_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_samples.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # 关联的QA记录ID, 删除时设置为NULL, 允许为空
    qa_record_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qa_records.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 关联的Agentic RAG执行记录ID, 删除时设置为NULL, 允许为空
    agent_run_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 执行时的问题快照
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # 生成答案
    generated_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 参考答案快照
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 检索结果摘要
    retrieved_chunks: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True
    )
    # 引用结果摘要
    citations: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # 检索相关性得分
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 回答质量得分
    answer_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 引用质量得分
    citation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 忠实度得分
    faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 综合得分
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 评测类型, manual / llm / rule
    judge_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 评分说明
    judge_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 样本执行耗时
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    __table_args__ = (
        Index("idx_eval_result_task_id", "task_id"),
        Index("idx_eval_result_sample_id", "sample_id"),
        Index("idx_eval_result_qa_id", "qa_record_id"),
        Index("idx_eval_result_status", "status"),
        Index("idx_eval_result_score", "overall_score"),
        Index("idx_eval_result_trace_id", "trace_id")
    )