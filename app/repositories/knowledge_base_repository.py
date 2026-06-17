from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseStatus


class KnowledgeBaseRepository:
    """
        知识库仓库
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        
    async def create(
        self,
        *,
        name: str,
        description: str | None,
        metadata: dict | None
    ) -> KnowledgeBase:
        """创建知识库
        Args:
            name: 知识库名称
            description: 知识库描述
            metadata: 元数据
        Returns:
            知识库实体
        """
        entity = KnowledgeBase(
            name=name,
            description=description,
            status = KnowledgeBaseStatus.ACTIVE,
            metadata_ = metadata
        )
        # ---------- 持久化操作 ----------
        # 将新创建的知识库实体对象添加到 SQLAlchemy 会话中。
        # add() 将实体置于 PENDING 状态，纳入会话的变更追踪，
        # 后续 flush() 时才会真正生成 INSERT 语句发送到数据库。
        self.session.add(entity)

        # 将会话中所有待处理的变更（含上一步 add 的 entity）同步刷新到数据库，
        # 执行 INSERT 语句让数据库生成主键 / 默认值等字段。
        # flush() 与 commit() 不同：flush 不提交事务，仅发送 SQL，
        # 后续可 rollback() 撤销；commit 则会结束当前事务。
        await self.session.flush()

        # flush() 之后 entity 虽已写入数据库，但某些字段（如自增 id、数据库默认值、
        # 触发器填充的字段等）尚未加载到 Python 端的对象中。
        # refresh() 从数据库重新查询该行的最新数据，将数据库生成的值同步到实体对象，
        # 确保返回的 entity 包含完整且最新的字段信息。
        await self.session.refresh(entity)

        # 返回已持久化且刷新完毕的知识库实体给调用方。
        # 此时 entity.id（主键）、entity.created_at 等数据库自增/默认字段均已可用。
        return entity
    
    async def get_by_id(
        self,
        knowledge_base_id: UUID,
        *,
        include_deleted: bool = False
    ) -> KnowledgeBase | None:
        """根据知识库 ID 获取知识库实体
        Args:
            knowledge_base_id: 知识库 ID
            include_deleted: 是否包含已删除的知识库
        Returns:
            知识库实体
        """
        stmt = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
        
        # 如果不包含已删除的知识库，添加状态和删除时间的查询条件
        if not include_deleted:
            stmt = stmt.where(
                KnowledgeBase.status != KnowledgeBaseStatus.DELETED.value,
                KnowledgeBase.deleted_at.is_(None)
            )
        
        # 执行查询并返回结果
        result = await self.session.execute(stmt)
        # 返回查询结果, scalar_one_or_none() 确保返回单个结果或 None
        return result.scalar_one_or_none()
    
    async def exists_active_name(
        self,
        name: str,
        *,
        exclude_id: UUID | None = None
    ) -> bool:
        """检查知识库名称是否已存在
        Args:
            name: 知识库名称
            exclude_id: 排除的知识库 ID
        Returns:
            是否存在
        """
        stmt = select(func.count()).select_from(KnowledgeBase).where(
            KnowledgeBase.name == name,
            KnowledgeBase.deleted_at.is_(None),
            KnowledgeBase.status != KnowledgeBaseStatus.DELETED.value
        )
        
        # 如果排除指定 ID，添加排除条件
        if exclude_id is not None:
            stmt = stmt.where(KnowledgeBase.id != exclude_id)
            
        # 执行查询并返回结果
        result = await self.session.execute(stmt)
        # 返回查询结果, scalar_one() 确保返回单个结果, 大于 0 表示存在
        return result.scalar_one() > 0
    
    async def list(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        keyword: str | None
    ) -> tuple[list[KnowledgeBase], int]:
        """
            分页查询知识库实体
            Args:
                page: 当前页码
                page_size: 每页记录数
                status: 状态
                keyword: 关键词
            Returns:
                知识库实体列表, 总记录数
        """
        
        # 构建查询条件
        filters = [
            KnowledgeBase.deleted_at.is_(None),
            KnowledgeBase.status != KnowledgeBaseStatus.DELETED.value
        ]
        
        # 如果指定状态，添加状态查询条件
        if status is not None:
            filters.append(KnowledgeBase.status == status)
            
        # 如果指定关键词，添加关键词查询条件
        if keyword:
            like_keyword = f"%{keyword}%"
            filters.append(
                or_(
                    KnowledgeBase.name.ilike(like_keyword),
                    KnowledgeBase.description.ilike(like_keyword)
                )
            )
        
        # 构造计数查询并应用过滤条件。
        # *filters 是 Python 的可迭代对象解包（unpacking）语法：
        # 将 filters 列表中的每个元素作为独立的 positional argument 传给 .where()。
        # 例如 filters = [cond1, cond2] 等价于 .where(cond1, cond2)，
        # 多个参数之间是 AND 关系（由 SQLAlchemy 隐式组合）。
        count_stmt = select(func.count()).select_from(KnowledgeBase).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()
        
        stmt = (
            select(KnowledgeBase)
            .where(*filters)
            .order_by(KnowledgeBase.id.desc())
            # offset: 跳过前 page - 1 页的数据
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        
        # 返回查询结果, scalars() 确保返回所有结果, as_list() 确保返回列表
        # total: 总记录数
        # page: 当前页码
        # page_size: 每页记录数
        # status: 状态
        # keyword: 关键词
        # 返回: 知识库实体列表, 总记录数
        return list(result.scalars().all()), total

        
    async def update(
        self,
        entity: KnowledgeBase,
        *,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        metadata: dict | None = None,
        update_metadata: bool = False
    ) -> KnowledgeBase:
        """
            更新知识库实体
            Args:
                entity: 知识库实体
                name: 知识库名称
                description: 知识库描述
                status: 状态
                metadata: 元数据
                update_metadata: 是否更新元数据
            Returns:
                更新后的知识库实体
        """
        if name is not None:
            entity.name = name
        if description is not None:
            entity.description = description
        if status is not None:
            entity.status = status
        if update_metadata:
            entity.metadata_ = metadata
            
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def soft_delete(
        self,
        entity: KnowledgeBase
    ) -> KnowledgeBase:
        """
            软删除知识库实体
            Args:
                entity: 知识库实体
            Returns:
                软删除后的知识库实体
        """
        entity.status = KnowledgeBaseStatus.DELETED.value
        entity.deleted_at = datetime.now(UTC)
        
        await self.session.flush()
        await self.session.refresh(entity)
        return entity