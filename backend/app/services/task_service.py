from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskCategory, TaskHistory
from app.models.tool import Tool
from app.schemas.task import (
    TaskCancel,
    TaskCategoryCreate,
    TaskCategoryUpdate,
    TaskCreate,
    TaskResolve,
    TaskUpdate,
)


class TaskService:
    """任务服务"""

    @staticmethod
    async def get_task_categories(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        stage: Optional[int] = None
    ) -> List[TaskCategory]:
        """获取任务分类列表"""
        query = select(TaskCategory)
        
        if stage is not None:
            query = query.where(TaskCategory.stage == stage)
        
        query = query.order_by(TaskCategory.name).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_task_category(db: AsyncSession, category_id: int) -> Optional[TaskCategory]:
        """获取单个任务分类"""
        result = await db.execute(
            select(TaskCategory).where(TaskCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_task_category(
        db: AsyncSession,
        category_data: TaskCategoryCreate
    ) -> TaskCategory:
        """创建任务分类"""
        category = TaskCategory(**category_data.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def update_task_category(
        db: AsyncSession,
        category_id: int,
        category_data: TaskCategoryUpdate
    ) -> Optional[TaskCategory]:
        """更新任务分类"""
        result = await db.execute(
            select(TaskCategory).where(TaskCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            return None
        
        update_data = category_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await db.commit()
        await db.refresh(category)
        return category

    @staticmethod
    async def delete_task_category(db: AsyncSession, category_id: int) -> bool:
        """删除任务分类"""
        result = await db.execute(
            select(TaskCategory).where(TaskCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            return False
        
        await db.delete(category)
        await db.commit()
        return True

    @staticmethod
    async def get_tasks(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        tool_id: Optional[int] = None,
        creator_id: Optional[int] = None,
        urgency: Optional[int] = None,
        force_shutdown: Optional[bool] = None,
        safety_hazard: Optional[bool] = None,
        open_only: bool = False,
        resolved_only: bool = False,
        project_id: Optional[int] = None,
    ) -> List[Task]:
        """获取任务列表"""
        query = select(Task).options(
            selectinload(Task.tool),
            selectinload(Task.creator),
            selectinload(Task.problem_category),
            selectinload(Task.resolver)
        )
        if project_id is not None:
            query = query.join(Tool, Tool.id == Task.tool_id)
        
        # 应用过滤条件
        filters = []
        if project_id is not None:
            filters.append(Tool.project_id == project_id)
        if tool_id:
            filters.append(Task.tool_id == tool_id)
        if creator_id:
            filters.append(Task.creator_id == creator_id)
        if urgency is not None:
            filters.append(Task.urgency == urgency)
        if force_shutdown is not None:
            filters.append(Task.force_shutdown == force_shutdown)
        if safety_hazard is not None:
            filters.append(Task.safety_hazard == safety_hazard)
        if open_only:
            filters.append(
                and_(
                    Task.cancelled == False,
                    Task.resolved == False
                )
            )
        if resolved_only:
            filters.append(Task.resolved == True)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(Task.creation_time.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_tasks(
        db: AsyncSession,
        tool_id: Optional[int] = None,
        creator_id: Optional[int] = None,
        urgency: Optional[int] = None,
        force_shutdown: Optional[bool] = None,
        safety_hazard: Optional[bool] = None,
        open_only: bool = False,
        resolved_only: bool = False,
        project_id: Optional[int] = None,
    ) -> int:
        query = select(func.count(Task.id))
        if project_id is not None:
            query = query.select_from(Task).join(Tool, Tool.id == Task.tool_id)

        filters = []
        if project_id is not None:
            filters.append(Tool.project_id == project_id)
        if tool_id:
            filters.append(Task.tool_id == tool_id)
        if creator_id:
            filters.append(Task.creator_id == creator_id)
        if urgency is not None:
            filters.append(Task.urgency == urgency)
        if force_shutdown is not None:
            filters.append(Task.force_shutdown == force_shutdown)
        if safety_hazard is not None:
            filters.append(Task.safety_hazard == safety_hazard)
        if open_only:
            filters.append(and_(Task.cancelled == False, Task.resolved == False))
        if resolved_only:
            filters.append(Task.resolved == True)
        if filters:
            query = query.where(and_(*filters))
        result = await db.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
        """获取单个任务"""
        result = await db.execute(
            select(Task)
            .options(
                selectinload(Task.tool),
                selectinload(Task.creator),
                selectinload(Task.problem_category),
                selectinload(Task.resolution_category),
                selectinload(Task.last_updated_by),
                selectinload(Task.resolver),
                selectinload(Task.history)
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_task(
        db: AsyncSession,
        task_data: TaskCreate,
        creator_id: int
    ) -> Task:
        """创建任务"""
        task_dict = task_data.model_dump()
        task_dict["creator_id"] = creator_id
        task_dict["creation_time"] = datetime.utcnow()
        
        task = Task(**task_dict)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # 创建初始历史记录
        history = TaskHistory(
            task_id=task.id,
            user_id=creator_id,
            status="Task created",
            time=task.creation_time
        )
        db.add(history)
        await db.commit()
        
        return task

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: int,
        task_data: TaskUpdate,
        updater_id: int
    ) -> Optional[Task]:
        """更新任务"""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.resolved or task.cancelled:
            raise ValueError("Cannot update a resolved or cancelled task")
        
        update_data = task_data.model_dump(exclude_unset=True)
        
        # 记录更新信息
        task.last_updated = datetime.utcnow()
        task.last_updated_by_id = updater_id
        
        for field, value in update_data.items():
            setattr(task, field, value)
        
        await db.commit()
        await db.refresh(task)
        
        # 创建历史记录
        history = TaskHistory(
            task_id=task.id,
            user_id=updater_id,
            status="Task updated",
            time=task.last_updated
        )
        db.add(history)
        await db.commit()
        
        return task

    @staticmethod
    async def resolve_task(
        db: AsyncSession,
        task_id: int,
        resolve_data: TaskResolve,
        resolver_id: int
    ) -> Optional[Task]:
        """解决任务"""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.resolved or task.cancelled:
            raise ValueError("Task is already resolved or cancelled")
        
        task.resolved = True
        task.resolution_time = datetime.utcnow()
        task.resolver_id = resolver_id
        task.resolution_description = resolve_data.resolution_description
        task.resolution_category_id = resolve_data.resolution_category_id
        task.last_updated = task.resolution_time
        task.last_updated_by_id = resolver_id
        
        await db.commit()
        await db.refresh(task)
        
        # 创建历史记录
        history = TaskHistory(
            task_id=task.id,
            user_id=resolver_id,
            status="Task resolved",
            time=task.resolution_time
        )
        db.add(history)
        await db.commit()
        
        return task

    @staticmethod
    async def cancel_task(
        db: AsyncSession,
        task_id: int,
        cancel_data: TaskCancel,
        canceller_id: int
    ) -> Optional[Task]:
        """取消任务"""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.resolved or task.cancelled:
            raise ValueError("Task is already resolved or cancelled")
        
        task.cancelled = True
        task.resolution_time = datetime.utcnow()
        task.resolver_id = canceller_id
        task.resolution_description = cancel_data.resolution_description
        task.last_updated = task.resolution_time
        task.last_updated_by_id = canceller_id
        
        await db.commit()
        await db.refresh(task)
        
        # 创建历史记录
        history = TaskHistory(
            task_id=task.id,
            user_id=canceller_id,
            status="Task cancelled",
            time=task.resolution_time
        )
        db.add(history)
        await db.commit()
        
        return task

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int) -> bool:
        """删除任务"""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return False
        
        await db.delete(task)
        await db.commit()
        return True

    @staticmethod
    async def get_task_history(
        db: AsyncSession,
        task_id: int
    ) -> List[TaskHistory]:
        """获取任务历史"""
        result = await db.execute(
            select(TaskHistory)
            .options(selectinload(TaskHistory.user))
            .where(TaskHistory.task_id == task_id)
            .order_by(TaskHistory.time.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_task_history(
        db: AsyncSession,
        task_id: int,
        user_id: int,
        status: str
    ) -> TaskHistory:
        """添加任务历史记录"""
        history = TaskHistory(
            task_id=task_id,
            user_id=user_id,
            status=status,
            time=datetime.utcnow()
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)
        return history

    @staticmethod
    async def get_urgent_tasks(
        db: AsyncSession,
        limit: int = 50,
        project_id: Optional[int] = None,
        creator_id: Optional[int] = None,
    ) -> List[Task]:
        """获取紧急任务"""
        query = (
            select(Task)
            .options(
                selectinload(Task.tool),
                selectinload(Task.creator)
            )
            .join(Tool, Tool.id == Task.tool_id)
        )
        filters = [
            or_(Task.force_shutdown == True, Task.safety_hazard == True),
            Task.cancelled == False,
            Task.resolved == False,
        ]
        if project_id is not None:
            filters.append(Tool.project_id == project_id)
        if creator_id is not None:
            filters.append(Task.creator_id == creator_id)
        result = await db.execute(
            query.where(and_(*filters))
            .order_by(Task.urgency.desc(), Task.creation_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
