from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse, success_response
from app.infrastructure.database.session import get_db_session
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeBaseWritableStatus,
)
from app.services.knowledge_base_service import KnowledgeBaseService

# prefix: 路由前缀，用于在URL中指定知识库相关的路由
# tags: 路由分组，用于在文档中组织路由
router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Base"])

def get_knowledge_base_service(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> KnowledgeBaseService:
    """
        获取知识库服务实例
        Args:
            session: 数据库会话
        Returns:
            知识库服务实例
    """
    return KnowledgeBaseService(session)

@router.post(
    # "": 路由路径，用于在URL中指定知识库相关的路由
    "",
    # response_model: 响应模型，用于指定成功创建知识库的响应模型, 
    response_model = ApiResponse[KnowledgeBaseResponse],
    # status_code: 响应状态码，用于指定成功创建知识库的响应状态码为201
    status_code = http_status.HTTP_201_CREATED,
    # summary: 路由摘要，用于在文档中显示路由的摘要
    summary = "创建知识库"
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
) -> ApiResponse[KnowledgeBaseResponse]:
    """
        创建知识库
        Args:
            payload: 知识库创建请求
        Returns:
            知识库响应
    """
    data = await service.create_knowledge_base(payload)
    return success_response(data=data)

@router.get(
    "",
    response_model=ApiResponse[KnowledgeBaseListResponse],
    summary="分页查询知识库列表"
)
async def list_knowledge_bases(
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: KnowledgeBaseWritableStatus | None = None,
    keyword: Annotated[str | None, Query(max_length=100)] = None
) -> ApiResponse[KnowledgeBaseListResponse]:
    """
        分页查询知识库列表
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态
            keyword: 关键词
        Returns:
            知识库列表响应
    """
    data = await service.list_knowledge_bases(
        page=page,
        page_size=page_size,
        status=status.value if status is not None else None,
        keyword=keyword
    )
    return success_response(data=data)

@router.get(
    "/{knowledge_base_id}",
    response_model=ApiResponse[KnowledgeBaseResponse],
    summary="查询知识库详情"
)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
) -> ApiResponse[KnowledgeBaseResponse]:
    """
        查询知识库详情
        Args:
            knowledge_base_id: 知识库ID
        Returns:
            知识库响应
    """
    data = await service.get_knowledge_base(knowledge_base_id)
    return success_response(data=data)


@router.patch(
    "/{knowledge_base_id}",
    response_model=ApiResponse[KnowledgeBaseResponse],
    summary="更新知识库"
)
async def update_knowledge_base(
    knowledge_base_id: UUID,
    payload: KnowledgeBaseUpdate,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
) -> ApiResponse[KnowledgeBaseResponse]:
    """
        更新知识库
        Args:
            knowledge_base_id: 知识库ID
            payload: 知识库更新请求
        Returns:
            知识库响应
    """
    data = await service.update_knowledge_base(knowledge_base_id, payload)
    return success_response(data=data)

@router.delete(
    "/{knowledge_base_id}",
    response_model=ApiResponse[KnowledgeBaseResponse],
    summary="软删除知识库"
)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    service: Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
) -> ApiResponse[KnowledgeBaseResponse]:
    """
        软删除知识库
        Args:
            knowledge_base_id: 知识库ID
        Returns:
            知识库响应
    """
    data = await service.deleted_knowledge_base(knowledge_base_id)
    return success_response(data=data)