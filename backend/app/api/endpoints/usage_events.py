from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.endpoints.auth import get_current_user
from app.core.audit import diff_payload, record_audit
from app.core.tool_permissions import require_tool_manager
from app.api.project_context import (
    CurrentProjectContext,
    get_current_project_context,
    get_tool_in_current_project,
    get_usage_event_in_current_project,
)
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project as ProjectModel
from app.schemas.usage_event import (
    UsageEventCreate,
    UsageEventDetail,
    UsageEventEnd,
    UsageEventResponse,
    UsageEventSyncResult,
    UsageEventStats,
    UsageEventUpdate,
)
from app.services.account_service import AccountService
from app.services.tool_service import ToolService
from app.services.usage_event_service import UsageEventService

router = APIRouter()


def _is_external_user(user: User | None) -> bool:
    if not user:
        return False
    auth_source = (getattr(user, "auth_source", None) or "local").lower()
    return (
        auth_source == "local"
        and not bool(getattr(user, "is_staff", False))
        and not bool(getattr(user, "is_superuser", False))
    )


@router.get("/", response_model=List[UsageEventResponse])
async def get_usage_events(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    tool_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    validated: Optional[bool] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    in_progress_only: bool = Query(False),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取使用记录列表"""
    # Determine effective user scope
    effective_user_id: Optional[int] = user_id
    if not current_user.is_staff and not current_user.is_superuser:
        effective_user_id = current_user.id
    elif current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools and tool_id is not None and int(tool_id) not in managed_tools:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if project_id is not None and int(project_id) != int(project_ctx.project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="project_id must match current project")
    project_id = project_ctx.project_id

    if status_filter is None and validated is not None:
        status_filter = "charged" if validated else "pending"

    # Auto-sync: ensure completed reservations are reflected in usage events.
    # Keep sync bounded so listing usage events stays responsive.
    lookback_days: Optional[int] = None
    if start_date is not None:
        delta_days = (datetime.now() - start_date.replace(tzinfo=None)).days
        lookback_days = max(1, min(3650, delta_days + 1))
    elif end_date is not None:
        delta_days = (datetime.now() - end_date.replace(tzinfo=None)).days
        lookback_days = max(1, min(3650, delta_days + 1))
    else:
        lookback_days = 30

    # For non-staff users we sync only their own reservations.
    await UsageEventService.sync_from_reservations(
        db,
        include_missed=False,
        lookback_days=lookback_days,
        user_id=effective_user_id,
        tool_id=tool_id,
        project_id=project_ctx.project_id,
    )

    try:
        items = await UsageEventService.get_usage_events(
            db,
            skip,
            limit,
            effective_user_id,
            tool_id,
            category_id,
            project_id,
            status_filter,
            in_progress_only,
            start_date,
            end_date,
        )
        total = await UsageEventService.count_usage_events(
            db,
            effective_user_id,
            tool_id,
            category_id,
            project_id,
            status_filter,
            in_progress_only,
            start_date,
            end_date,
        )
        if current_user.is_staff and not current_user.is_superuser:
            managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
            if managed_tools:
                items = [item for item in items if int(getattr(item, "tool_id", 0) or 0) in managed_tools]
                total = len(items)
        response.headers["X-Total-Count"] = str(total)
        return items
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/", response_model=UsageEventResponse, status_code=status.HTTP_201_CREATED)
async def create_usage_event(
    event: UsageEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建使用记录（开始使用工具）"""
    # 普通用户只能为自己开启
    if not current_user.is_staff and not current_user.is_superuser:
        if not getattr(current_user, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not verified",
            )
        event.user_id = current_user.id
        event.operator_id = current_user.id

    await get_tool_in_current_project(db, event.tool_id, project_ctx)
    tool_service = ToolService(db)
    usage_user = await db.get(User, event.user_id)
    if not usage_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not getattr(usage_user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive")
    if _is_external_user(usage_user) and not getattr(usage_user, "is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not verified",
        )
    if not await tool_service.check_external_user_tool_access(event.tool_id, usage_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有使用该仪器的权限，请联系管理员申请授权",
        )
    if event.project_id is not None and int(event.project_id) != int(project_ctx.project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usage event project must match current project")
    event.project_id = project_ctx.project_id

    # 校验项目状态（访问权限已由 current_project_context 统一校验）
    project = (await db.execute(select(ProjectModel).where(ProjectModel.id == event.project_id))).scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is inactive")

    preferred_payer_account_id = event.payer_account_id
    if not (current_user.is_staff or current_user.is_superuser):
        preferred_payer_account_id = None
    payer_account = await AccountService.resolve_reservable_account_for_user(
        db,
        event.user_id,
        project_id=project_ctx.project_id,
        preferred_account_id=preferred_payer_account_id,
        require_reservable=False,
    )
    if payer_account is None:
        if _is_external_user(usage_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前外部用户尚未配置所属账户，请联系管理员配置，或先申请加入账户并等待审批生效",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前使用用户没有可用的付款账户")
    if not current_user.is_superuser:
        if not await AccountService.account_can_reserve(db, payer_account.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="付款账户余额或信用额度不足，当前不允许开始使用",
            )
    event.payer_account_id = payer_account.id

    # 检查工具是否已被占用
    active_usage = await UsageEventService.get_active_usage_for_tool(db, event.tool_id)
    if active_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool is currently in use by user {active_usage.user_id}"
        )
    
    try:
        return await UsageEventService.create_usage_event(db, event, current_user.id)
    except ValueError as exc:
        await db.rollback()
        status_code = (
            status.HTTP_409_CONFLICT
            if "currently in use" in str(exc) or "already in use" in str(exc)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/stats", response_model=UsageEventStats)
async def get_usage_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tool_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    validated: Optional[bool] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取使用统计"""
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)

    # 普通用户只能查看自己的统计
    if not current_user.is_staff and not current_user.is_superuser:
        user_id = current_user.id

    if status_filter is None and validated is not None:
        status_filter = "charged" if validated else "pending"

    try:
        return await UsageEventService.get_usage_stats(
            db,
            start_date,
            end_date,
            tool_id,
            user_id,
            category_id,
            project_ctx.project_id,
            status_filter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sync-from-reservations", response_model=UsageEventSyncResult)
async def sync_usage_from_reservations(
    include_missed: bool = Query(False, description="是否包含 missed 的预约"),
    lookback_days: Optional[int] = Query(None, ge=1, le=3650, description="只同步最近 N 天内结束的预约"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """将已完成的预约同步到使用记录（需要 staff 权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can sync usage events from reservations",
        )
    if getattr(current_user, "managed_tool_ids_list", []) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool-specific administrators should sync usage from their tool's reservation completion flow",
        )

    return await UsageEventService.sync_from_reservations(
        db,
        include_missed=include_missed,
        lookback_days=lookback_days,
        project_id=project_ctx.project_id,
    )


@router.get("/{event_id}", response_model=UsageEventDetail)
async def get_usage_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取使用记录详情"""
    event = await get_usage_event_in_current_project(db, event_id, project_ctx)
    
    # 添加计算属性
    response = UsageEventDetail.model_validate(event)
    response.duration_minutes = event.duration_minutes()
    response.is_in_progress = event.is_in_progress
    response.self_usage = event.self_usage()
    
    return response


@router.post("/{event_id}/end", response_model=UsageEventResponse)
async def end_usage_event(
    event_id: int,
    end_data: UsageEventEnd = Body(default_factory=UsageEventEnd),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """结束使用记录"""
    event = await get_usage_event_in_current_project(db, event_id, project_ctx)
    
    # 只有操作员或管理员可以结束使用
    if event.operator_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the operator or staff can end this usage"
        )
    if current_user.is_staff and event.operator_id != current_user.id:
        require_tool_manager(current_user, event.tool_id)
    
    try:
        return await UsageEventService.end_usage_event(db, event_id, end_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{event_id}", response_model=UsageEventResponse)
async def update_usage_event(
    event_id: int,
    event: UsageEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新使用记录（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can update usage events"
        )
    
    existing = await get_usage_event_in_current_project(db, event_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    before_snapshot = {
        "end": getattr(existing, "end", None),
        "actual_duration_minutes": getattr(existing, "actual_duration_minutes", None),
        "validated": getattr(existing, "validated", None),
        "amount": getattr(existing, "amount", None),
        "note": getattr(existing, "note", None),
    }
    try:
        updated = await UsageEventService.update_usage_event(db, event_id, event)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage event not found"
        )
    after_snapshot = {
        "end": getattr(updated, "end", None),
        "actual_duration_minutes": getattr(updated, "actual_duration_minutes", None),
        "validated": getattr(updated, "validated", None),
        "amount": getattr(updated, "amount", None),
        "note": getattr(updated, "note", None),
    }
    await record_audit(
        db,
        user_id=current_user.id,
        action="USAGE_EVENT_UPDATE",
        detail={
            "event_id": int(event_id),
            "project_id": project_ctx.project_id,
            "changes": diff_payload(before_snapshot, after_snapshot),
        },
    )
    return updated


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_usage_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """删除使用记录（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can delete usage events"
        )
    
    existing = await get_usage_event_in_current_project(db, event_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    snapshot = {
        "user_id": getattr(existing, "user_id", None),
        "tool_id": getattr(existing, "tool_id", None),
        "amount": getattr(existing, "amount", None),
        "validated": getattr(existing, "validated", None),
        "waived": getattr(existing, "waived", None),
    }
    deleted = await UsageEventService.delete_usage_event(db, event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage event not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="USAGE_EVENT_DELETE",
        detail={
            "event_id": int(event_id),
            "project_id": project_ctx.project_id,
            "snapshot": snapshot,
        },
    )


@router.get("/tool/{tool_id}/active", response_model=Optional[UsageEventResponse])
async def get_active_usage_for_tool(
    tool_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取工具当前的使用记录"""
    await get_tool_in_current_project(db, tool_id, project_ctx)
    if current_user.is_staff:
        require_tool_manager(current_user, tool_id)
    event = await UsageEventService.get_active_usage_for_tool(db, tool_id)
    if not event:
        return None
    if int(event.project_id) != int(project_ctx.project_id):
        return None
    return event


@router.get("/user/{user_id}/active", response_model=List[UsageEventResponse])
async def get_active_usage_for_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取用户当前的所有使用记录"""
    # 只能查看自己的或管理员可以查看所有
    if user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own active usage"
        )
    
    events = await UsageEventService.get_active_usage_for_user(db, user_id)
    return [event for event in events if int(getattr(event, "project_id", 0) or 0) == int(project_ctx.project_id)]


@router.post("/{event_id}/validate", response_model=UsageEventResponse)
async def validate_usage_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """验证使用记录（需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can validate usage events"
        )
    
    existing = await get_usage_event_in_current_project(db, event_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    event = await UsageEventService.validate_usage_event(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage event not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="USAGE_EVENT_VALIDATE",
        detail={
            "event_id": int(event_id),
            "project_id": project_ctx.project_id,
            "amount": getattr(event, "amount", None),
        },
    )
    return event


@router.post("/{event_id}/waive", response_model=UsageEventResponse)
async def waive_usage_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """豁免使用记录（不计费，需要管理员权限）"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can waive usage events"
        )
    
    existing = await get_usage_event_in_current_project(db, event_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    pre_amount = getattr(existing, "amount", None)
    event = await UsageEventService.waive_usage_event(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage event not found"
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="USAGE_EVENT_WAIVE",
        detail={
            "event_id": int(event_id),
            "project_id": project_ctx.project_id,
            "amount_before_waive": pre_amount,
            "user_id": getattr(event, "user_id", None),
        },
    )
    return event


@router.post("/{event_id}/reactivate", response_model=UsageEventResponse)
async def reactivate_usage_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """重新激活已豁免的使用记录（需要管理员权限）。

    激活后将恢复为已验证状态。
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can reactivate usage events",
        )

    existing = await get_usage_event_in_current_project(db, event_id, project_ctx)
    require_tool_manager(current_user, existing.tool_id)
    event = await UsageEventService.reactivate_usage_event(db, event_id, current_user.id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usage event not found",
        )
    await record_audit(
        db,
        user_id=current_user.id,
        action="USAGE_EVENT_REACTIVATE",
        detail={
            "event_id": int(event_id),
            "project_id": project_ctx.project_id,
            "amount": getattr(event, "amount", None),
            "user_id": getattr(event, "user_id", None),
        },
    )
    return event
