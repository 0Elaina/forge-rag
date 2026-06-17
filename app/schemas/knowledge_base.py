# 前向引用
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseStatus(StrEnum):
    """知识库状态枚举"""
    # 活动状态
    ACTIVE = "active"
    # 禁用状态
    DISABLED = "disabled"
    # 删除状态
    DELETED = "deleted"
    
class KnowledgeBaseWritableStatus(StrEnum):
    """知识库可写状态枚举"""
    # 可写状态
    ACTIVE = "active"
    # 禁用状态
    DISABLED = "disabled"
    
class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求模型"""
    # 知识库名称
    name: str = Field(min_length=1, max_length=100)
    # 知识库描述
    description: str | None = None
    # 元数据
    metadata: dict[str, Any] | None = None
    
class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求模型"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: KnowledgeBaseWritableStatus | None = None
    metadata: dict[str, Any] | None = None
    
class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: UUID
    name: str
    description: str | None
    status: KnowledgeBaseWritableStatus
    document_count: int
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    
    @classmethod
    def from_entity(cls, entity: Any) -> KnowledgeBaseResponse:
        """从知识库实体创建知识库响应模型
        Args:
            entity: 知识库实体
        Returns:
            知识库响应模型
        """
        return cls(
            id = entity.id,
            name = entity.name,
            description = entity.description,
            status = entity.status,
            document_count = entity.document_count,
            metadata = entity.metadata_,
            created_at = entity.created_at,
            updated_at = entity.updated_at,
            deleted_at = entity.deleted_at
        )
    
class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应模型"""
    # 知识库列表
    items: list[KnowledgeBaseResponse]
    # 当前页码
    page: int
    # 每页数量
    page_size: int
    # 总页数
    total: int