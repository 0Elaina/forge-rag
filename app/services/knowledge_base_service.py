from uuid import UUID

# IntegrityError: 数据库完整性约束冲突
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    BusinessException,
    KnowledgeBaseDisabledException,
    KnowledgeBaseNotFoundException,
)
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseStatus,
    KnowledgeBaseUpdate,
)


class KnowledgeBaseService:
    def __init__(self, session: AsyncSession):
        """
            知识库服务
            Args:
                session: 数据库会话
            Returns:
                知识库服务实例
        """
        # 初始化数据库会话
        # 用于执行数据库操作，如查询、插入、更新、删除等。
        self.session = session
        # 初始化
        self.repository = KnowledgeBaseRepository(session)
        
    async def create_knowledge_base(
        self,
        payload: KnowledgeBaseCreate
    ) -> KnowledgeBaseResponse:
        """
            创建知识库
            Args:
                payload: 知识库创建请求
            Returns:
                知识库响应
        """
        # strip(): 移除字符串首尾的空格
        name = payload.name.strip()
        
        # 检查知识库名称是否已存在
        if await self.repository.exists_active_name(name):
            raise BusinessException("知识库名称已存在")
        
        try:
            entity = await self.repository.create(
                name = name,
                description = payload.description,
                metadata = payload.metadata
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            # from exc: 保留原始异常信息，方便调试和定位问题
            raise BusinessException("知识库已经存在") from exc
        except Exception:
            await self.session.rollback()
            raise
        # 返回创建的知识库响应
        return KnowledgeBaseResponse.from_entity(entity)
    
    async def list_knowledge_bases(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        keyword: str | None
    ) -> KnowledgeBaseListResponse:
        """
            列出知识库
            Args:
                page: 页码
                page_size: 每页数量
                status: 状态
                keyword: 关键词
            Returns:
                知识库列表响应
        """
        items, total = await self.repository.list(
            page = page,
            page_size = page_size,
            status = status,
            keyword = keyword.strip() if keyword else None
        )
        
        # 返回知识库列表响应
        # items: 知识库实体列表
        # page: 当前页码
        # page_size: 每页数量
        # total: 总记录数
        return KnowledgeBaseListResponse(
            items = [KnowledgeBaseResponse.from_entity(item) for item in items],
            page = page,
            page_size = page_size,
            total = total
        )

    async def get_knowledge_base(
        self,
        knowledge_base_id: UUID
    ) -> KnowledgeBaseResponse:
        """
            获取知识库
            Args:
                knowledge_base_id: 知识库ID
            Returns:
                知识库响应
        """
        entity = await self.repository.get_by_id(knowledge_base_id)
        
        if not entity:
            raise KnowledgeBaseNotFoundException()
        
        return KnowledgeBaseResponse.from_entity(entity)
    
    async def update_knowledge_base(
        self,
        knowledge_base_id: UUID,
        payload: KnowledgeBaseUpdate
    ) -> KnowledgeBaseResponse:
        """
            更新知识库
            Args:
                knowledge_base_id: 知识库ID
                payload: 知识库更新请求
            Returns:
                知识库响应
        """
        entity = await self.repository.get_by_id(knowledge_base_id)
        
        # 检查知识库是否存在
        if not entity:
            # 抛出知识库不存在异常
            raise KnowledgeBaseNotFoundException()
        
        '''
            update_data:
                model_dump: 将模型实例转换为字典
                exclude_unset: 排除未设置的字段
            转为update_data的目的是:
                1. 从模型实例中提取需要更新的字段
                2. 排除未设置的字段
                3. 保留其他字段
        '''
        update_data = payload.model_dump(exclude_unset=True)
        name = update_data.get("name")
        
        if name is not None:
            name = name.strip()
            # exclude_id: 排除当前知识库ID
            if await self.repository.exists_active_name(name, exclude_id=knowledge_base_id):
                raise BusinessException("知识库名称已存在")
            
        try:
            updated = await self.repository.update(
                entity,
                name=name,
                # get(): 从字典中获取值，如果键不存在则返回 None
                description=update_data.get("description"),
                # 此处如果用get(), 会出现None.value, 直接报错
                # status的值是枚举类型, 直接赋值会报错, 所以需要获取枚举值的value
                status=update_data["status"].value if "status" in update_data else None,
                metadata=update_data.get("metadata"),
                update_metadata="metadata" in update_data
            )
            await self.session.commit()
        # IntegrityError: 数据库完整性约束冲突
        except IntegrityError as exc:
            await self.session.rollback()
            # from exc: 保留原始异常信息，方便调试和定位问题
            raise BusinessException("数据库完整性约束冲突") from exc
        except Exception:
            await self.session.rollback()
            raise
        
        return KnowledgeBaseResponse.from_entity(updated)
    
    async def deleted_knowledge_base(
        self,
        knowledge_base_id: UUID
    ) -> KnowledgeBaseResponse:
        """
            软删除知识库
            Args:
                knowledge_base_id: 知识库ID
            Returns:
                知识库响应
        """
        entity = await self.repository.get_by_id(knowledge_base_id)
        
        if not entity:
            raise KnowledgeBaseNotFoundException()
        
        try:
            deleted = await self.repository.soft_delete(entity)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        
        return KnowledgeBaseResponse.from_entity(deleted)

    async def ensure_knowledge_base_available(
        self,
        knowledge_base_id: UUID
    ) -> KnowledgeBaseResponse:
        """
            确保知识库可用
            Args:
                knowledge_base_id: 知识库ID
            Returns:
                知识库响应
        """
        entity = await self.repository.get_by_id(
            knowledge_base_id,
            include_deleted=True
        )
        
        if entity is None or entity.status == KnowledgeBaseStatus.DELETED.value:
            raise KnowledgeBaseNotFoundException()
        
        if entity.status == KnowledgeBaseStatus.DISABLED.value:
            raise KnowledgeBaseDisabledException()