from app.infrastructure.database.models.document import Document
from app.infrastructure.database.models.document_chunk import DocumentChunk
from app.infrastructure.database.models.knowledge_base import KnowledgeBase

# __all__ 控制 from database import * 时的导出白名单，仅暴露三个 ORM 模型
__all__ = [
    # 文档模型 — 对应 documents 表
    "Document",
    # 文档分块模型 — 对应 document_chunks 表
    "DocumentChunk",
    # 知识库模型 — 对应 knowledge_bases 表
    "KnowledgeBase",
]