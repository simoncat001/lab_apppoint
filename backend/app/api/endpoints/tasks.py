from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import (
    CurrentProjectContext,
    ensure_project_id_matches_current_project,
    get_current_project_context,
    get_tool_in_current_project,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCancel,
    TaskCategoryCreate,
    TaskCategoryResponse,
    TaskCategoryUpdate,
    TaskCreate,
    TaskDetail,
    TaskHistoryResponse,
    TaskResolve,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter()


async def _get_task_in_current_project(
    db: AsyncSession,
    task_id: int,
    project_ctx: CurrentProjectContext,
):
    task = await TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    ensure_project_id_matches_current_project(
        getattr(getattr(task, "tool", None), "project_id", None),
        project_ctx,
        detail_prefix="Task",
    )
    return task


# TaskCategory endpoints
@router.get("/task-categories", response_model=List[TaskCategoryResponse])
async def get_task_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    stage: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取任务分类列表"""
    return await TaskService.get_task_categories(db, skip, limit, stage)


@router.post("/task-categories", response_model=TaskCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_task_category(
    category: TaskCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建任务分类（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can create task categories"
        )
    return await TaskService.create_task_category(db, category)


@router.get("/task-categories/{category_id}", response_model=TaskCategoryResponse)
async def get_task_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取任务分类详情"""
    category = await TaskService.get_task_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task category not found"
        )
    return category


@router.put("/task-categories/{category_id}", response_model=TaskCategoryResponse)
async def update_task_category(
    category_id: int,
    category: TaskCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新任务分类（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can update task categories"
        )
    
    updated = await TaskService.update_task_category(db, category_id, category)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task category not found"
        )
    return updated


@router.delete("/task-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除任务分类（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can delete task categories"
        )
    
    deleted = await TaskService.delete_task_category(db, category_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task category not found"
        )


# Task endpoints
@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tool_id: Optional[int] = Query(None),
    creator_id: Optional[int] = Query(None),
    urgency: Optional[int] = Query(None),
    force_shutdown: Optional[bool] = Query(None),
    safety_hazard: Optional[bool] = Query(None),
    open_only: bool = Query(False),
    resolved_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取任务列表"""
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)
    if not (current_user.is_staff or current_user.is_superuser):
        creator_id = current_user.id
    items = await TaskService.get_tasks(
        db, skip, limit, tool_id, creator_id, urgency,
        force_shutdown, safety_hazard, open_only, resolved_only,
        project_id=project_ctx.project_id,
    )
    total = await TaskService.count_tasks(
        db, tool_id, creator_id, urgency,
        force_shutdown, safety_hazard, open_only, resolved_only,
        project_id=project_ctx.project_id,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建任务"""
    await get_tool_in_current_project(db, task.tool_id, project_ctx)
    return await TaskService.create_task(db, task, current_user.id)


@router.get("/urgent", response_model=List[TaskResponse])
async def get_urgent_tasks(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取紧急任务列表"""
    creator_id = None if (current_user.is_staff or current_user.is_superuser) else current_user.id
    return await TaskService.get_urgent_tasks(
        db,
        limit,
        project_id=project_ctx.project_id,
        creator_id=creator_id,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新任务（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can update tasks"
        )
    
    try:
        await _get_task_in_current_project(db, task_id, project_ctx)
        updated = await TaskService.update_task(db, task_id, task, current_user.id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return updated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/resolve", response_model=TaskResponse)
async def resolve_task(
    task_id: int,
    resolve_data: TaskResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """解决任务（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can resolve tasks"
        )
    
    try:
        await _get_task_in_current_project(db, task_id, project_ctx)
        task = await TaskService.resolve_task(db, task_id, resolve_data, current_user.id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: int,
    cancel_data: TaskCancel,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """取消任务（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can cancel tasks"
        )
    
    try:
        await _get_task_in_current_project(db, task_id, project_ctx)
        task = await TaskService.cancel_task(db, task_id, cancel_data, current_user.id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除任务（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can delete tasks"
        )
    
    await _get_task_in_current_project(db, task_id, project_ctx)
    deleted = await TaskService.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.get("/{task_id}/history", response_model=List[TaskHistoryResponse])
async def get_task_history(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取任务历史"""
    task = await _get_task_in_current_project(db, task_id, project_ctx)
    if (
        not (current_user.is_staff or current_user.is_superuser)
        and task.creator_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    return await TaskService.get_task_history(db, task_id)


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取任务详情"""
    task = await _get_task_in_current_project(db, task_id, project_ctx)
    if (
        not (current_user.is_staff or current_user.is_superuser)
        and task.creator_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # 添加状态显示
    response = TaskDetail.model_validate(task)
    response.status_display = task.status_display

    return response
