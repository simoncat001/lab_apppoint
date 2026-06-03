"""
Reservation API endpoints
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.project_context import (
    CurrentProjectContext,
    get_current_project_context,
    get_reservation_in_current_project,
    get_tool_in_current_project,
)
from app.schemas.reservation import (
    Reservation,
    ReservationCreate,
    ReservationUpdate,
    ReservationOccupiedSlot,
    ReservationPaymentRequest,
    ReservationCompletionRequest,
)
from app.services.reservation_service import ReservationAvailabilityError, ReservationService
from app.services.usage_event_service import UsageEventService
from app.services.project_service import ProjectService
from app.api.endpoints.auth import get_current_user
from app.models.user import User
from app.models.reservation import Reservation as ReservationModel
from app.models.project import Project as ProjectModel
from app.core.config import settings
from app.models.audit_log import AuditLog
from app.services.account_service import AccountService
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()


def _is_external_user(user: User | None) -> bool:
    if not user:
        return False
    auth_source = (getattr(user, "auth_source", None) or "local").lower()
    return auth_source == "local" and not bool(getattr(user, "is_superuser", False))


def _is_start_time_in_past(start_time: datetime) -> bool:
    if getattr(start_time, "tzinfo", None) is not None:
        now = datetime.now(tz=start_time.tzinfo)
    else:
        now = datetime.now()
    return start_time < now


def _day_bounds(value: datetime) -> tuple[datetime, datetime]:
    day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def _normalize_count_based_reservation_window(value: datetime) -> tuple[datetime, datetime]:
    day_start, day_end = _day_bounds(value)
    return day_start, day_end - timedelta(seconds=1)


def _to_naive_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


async def _resolve_reservation_payer_account_id(
    db: AsyncSession,
    *,
    reservation_user_id: int,
    project_id: int,
    preferred_account_id: Optional[int],
    enforce_reservable: bool = True,
) -> int:
    payer_account = await AccountService.resolve_reservable_account_for_user(
        db,
        reservation_user_id,
        project_id=project_id,
        preferred_account_id=preferred_account_id,
        require_reservable=False,
    )
    reservation_user = await db.get(User, reservation_user_id)
    if payer_account is None:
        if _is_external_user(reservation_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前外部用户尚未配置所属账户，请联系管理员配置，或先申请加入账户并等待审批生效",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前预约用户没有可用于本项目预约的付款账户",
        )
    if enforce_reservable and not await AccountService.account_can_reserve(db, payer_account.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="付款账户余额或信用额度不足，当前不允许预约",
        )
    return int(payer_account.id)


@router.get("/", response_model=List[Reservation])
async def get_reservations(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    tool_id: int = None,
    category_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    include_all: bool = False,
    cancelled: bool | None = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取预约列表"""
    # 普通用户只能查看自己的预约
    if not current_user.is_staff and not current_user.is_superuser:
        if not include_all:
            user_id = current_user.id
    elif current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools:
            # 如果没有指定 tool_id，则限定在可管理范围内
            if tool_id is None:
                # Apply scope by picking first tool and letting service filter? We'll post-filter.
                pass
    
    service = ReservationService(db)
    reservations = await service.get_reservations(
        skip=skip,
        limit=limit,
        user_id=user_id,
        tool_id=tool_id,
        project_id=project_ctx.project_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        cancelled=cancelled,
    )
    if current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools:
            reservations = [r for r in reservations if r.tool_id in managed_tools]
    if include_all and not current_user.is_staff and not current_user.is_superuser:
        for r in reservations:
            if r.user_id != current_user.id:
                r.user = None
                r.project = None
                r.additional_information = ""
                r.payment_status = None
                r.payment_amount = None
                r.payment_method = None
                r.paid_at = None
                r.actual_start = None
                r.actual_end = None
                r.completion_note = None
                r.completed_by_id = None
                r.completed_at = None

    if current_user.is_staff and not current_user.is_superuser and getattr(current_user, "managed_tool_ids_list", []):
        total = len(reservations)
    else:
        total = await service.count_reservations(
            user_id=user_id,
            tool_id=tool_id,
            project_id=project_ctx.project_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            cancelled=cancelled,
        )
    response.headers["X-Total-Count"] = str(total)
    return reservations


@router.get("/today", response_model=List[Reservation])
async def get_today_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """今日预约列表（管理员）"""
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can view today reservations")

    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    service = ReservationService(db)
    reservations = await service.get_reservations(
        start_date=start,
        end_date=end,
        project_id=project_ctx.project_id,
        skip=0,
        limit=1000,
    )
    if current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools:
            reservations = [r for r in reservations if r.tool_id in managed_tools]
    return reservations


@router.get("/occupied", response_model=List[ReservationOccupiedSlot])
async def get_occupied_reservation_slots(
    tool_id: int,
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取当前项目下某台仪器在指定范围内的已占用时段"""
    if not current_user.is_staff and not current_user.is_superuser:
        if not getattr(current_user, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not verified",
            )

    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )

    await get_tool_in_current_project(db, tool_id, project_ctx)

    service = ReservationService(db)
    reservations = await service.get_occupied_slots(
        tool_id=tool_id,
        project_id=project_ctx.project_id,
        start_date=start_date,
        end_date=end_date,
    )
    return reservations


@router.get("/{reservation_id:int}", response_model=Reservation)
async def get_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取单个预约"""
    reservation = await get_reservation_in_current_project(db, reservation_id, project_ctx)
    
    # 权限检查
    if not current_user.is_staff and not current_user.is_superuser:
        if reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this reservation"
            )
            
    return reservation


@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    reservation_in: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """创建新预约"""
    # 普通用户只能给自己预约
    if not current_user.is_staff and not current_user.is_superuser:
        if not getattr(current_user, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not verified",
            )
        reservation_in.user_id = current_user.id

    service = ReservationService(db)

    if reservation_in.tool_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tool is required")

    tool = await get_tool_in_current_project(db, reservation_in.tool_id, project_ctx)

    # 设备级权限检查：外部用户访问受限仪器需要单独授权
    from app.services.tool_service import ToolService
    tool_service = ToolService(db)
    if not await tool_service.check_external_user_tool_access(reservation_in.tool_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有使用该仪器的权限，请联系管理员申请授权",
        )

    is_count_based_tool = int(getattr(tool, "price_type", 1) or 1) == 0

    tool_bound_project_id = getattr(tool, "project_id", None)
    if tool_bound_project_id is not None:
        reservation_in.project_id = tool_bound_project_id
    elif reservation_in.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool has no bound project configured",
        )

    if reservation_in.project_id is not None and int(reservation_in.project_id) != int(project_ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation project must match current project",
        )

    # 校验项目：项目账户作为收款账户保留，付款账户从预约用户侧解析
    project = (
        await db.execute(select(ProjectModel).where(ProjectModel.id == project_ctx.project_id))
    ).scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not project.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is inactive")

    if project.account_id is None:
        # Auto-heal historical/mirrored projects missing local account binding.
        project = await ProjectService(db).ensure_org_account_for_project(project.id) or project
    if project.account_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not bound to an account")

    reservation_in.project_id = project_ctx.project_id

    reservation_in.payer_account_id = await _resolve_reservation_payer_account_id(
        db,
        reservation_user_id=reservation_in.user_id,
        project_id=project_ctx.project_id,
        preferred_account_id=reservation_in.payer_account_id,
        enforce_reservable=not current_user.is_superuser,
    )
    
    # 验证时间
    if is_count_based_tool:
        day_start, day_end = _day_bounds(reservation_in.start)
        today_start, _ = _day_bounds(datetime.now(tz=reservation_in.start.tzinfo) if getattr(reservation_in.start, "tzinfo", None) else datetime.now())
        if day_start < today_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="预约日期不能早于今天",
            )
        reservation_in.start, reservation_in.end = _normalize_count_based_reservation_window(reservation_in.start)
        daily_quota = int(getattr(tool, "maximum_reservations_per_day", 0) or 0)
        if daily_quota > 0:
            reserved_count = await service.count_reservations_for_day(
                tool_id=reservation_in.tool_id,
                day_start=day_start,
                day_end=day_end,
            )
            if reserved_count >= daily_quota:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="当天预约次数已满，无法继续预约",
                )
    else:
        if reservation_in.start >= reservation_in.end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        if _is_start_time_in_past(reservation_in.start):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time cannot be earlier than current time",
            )

        # 检查冲突
        has_conflict = await service.check_reservation_conflict(
            tool_id=reservation_in.tool_id,
            start=reservation_in.start,
            end=reservation_in.end
        )
        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Time slot is already reserved"
            )
    
    try:
        reservation = await service.create_reservation(reservation_in, creator_id=current_user.id)
    except ReservationAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return reservation


@router.put("/{reservation_id:int}", response_model=Reservation)
async def update_reservation(
    reservation_id: int,
    reservation_in: ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """更新预约"""
    reservation = await get_reservation_in_current_project(db, reservation_id, project_ctx)

    # 权限：管理员可更新所有；普通用户只能更新自己的预约
    if not current_user.is_staff and not current_user.is_superuser:
        if reservation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        # 普通用户不能修改支付/完成/取消状态字段
        blocked_fields = {
            "cancelled",
            "payment_status",
            "payment_amount",
            "payment_method",
            "paid_at",
            "actual_start",
            "actual_end",
            "completion_note",
            "completed_by_id",
            "completed_at",
        }
        update_payload = reservation_in.model_dump(exclude_unset=True)
        if any(field in update_payload for field in blocked_fields):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    else:
        update_payload = reservation_in.model_dump(exclude_unset=True)

    if "project_id" in update_payload and update_payload["project_id"] is not None:
        if int(update_payload["project_id"]) != int(project_ctx.project_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation must stay in current project")

    service = ReservationService(db)
    if "start" in update_payload or "end" in update_payload:
        effective_start = update_payload.get("start", reservation.start)
        effective_end = update_payload.get("end", reservation.end)
        if effective_start is None or effective_end is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start and end time are required",
            )
        tool = await get_tool_in_current_project(db, reservation.tool_id, project_ctx)
        is_count_based_tool = int(getattr(tool, "price_type", 1) or 1) == 0
        if is_count_based_tool:
            day_start, day_end = _day_bounds(effective_start)
            daily_quota = int(getattr(tool, "maximum_reservations_per_day", 0) or 0)
            normalized_start, normalized_end = _normalize_count_based_reservation_window(effective_start)
            reservation_in.start = normalized_start
            reservation_in.end = normalized_end
            if daily_quota > 0:
                reserved_count = await service.count_reservations_for_day(
                    tool_id=reservation.tool_id,
                    day_start=day_start,
                    day_end=day_end,
                    exclude_id=reservation_id,
                )
                if reserved_count >= daily_quota:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="当天预约次数已满，无法调整到该日期",
                    )
        else:
            if effective_start >= effective_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End time must be after start time",
                )
            has_conflict = await service.check_reservation_conflict(
                tool_id=reservation.tool_id,
                start=effective_start,
                end=effective_end,
                exclude_id=reservation_id,
            )
            if has_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Time slot is already reserved",
                )

    if "payer_account_id" in update_payload:
        reservation_in.payer_account_id = await _resolve_reservation_payer_account_id(
            db,
            reservation_user_id=reservation.user_id,
            project_id=project_ctx.project_id,
            preferred_account_id=reservation_in.payer_account_id,
            enforce_reservable=not current_user.is_superuser,
        )

    try:
        reservation = await service.update_reservation(reservation_id, reservation_in)
    except ReservationAvailabilityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )
    return reservation


@router.delete("/{reservation_id:int}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """取消预约"""
    reservation = await get_reservation_in_current_project(db, reservation_id, project_ctx)

    if reservation.payment_status == "PAID" and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid reservations cannot be cancelled"
        )

    if not current_user.is_staff and not current_user.is_superuser:
        if reservation.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        limit = settings.RESERVATION_CANCEL_LIMIT_PER_MONTH
        if limit is not None:
            now = datetime.utcnow()
            start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_month.month == 12:
                next_month = start_month.replace(year=start_month.year + 1, month=1)
            else:
                next_month = start_month.replace(month=start_month.month + 1)

            result = await db.execute(
                select(func.count())
                .select_from(ReservationModel)
                .where(
                    ReservationModel.user_id == current_user.id,
                    ReservationModel.project_id == project_ctx.project_id,
                    ReservationModel.cancellation_time.isnot(None),
                    ReservationModel.cancellation_time >= start_month,
                    ReservationModel.cancellation_time < next_month,
                )
            )
            cancelled_count = result.scalar_one()
            if cancelled_count >= limit:
                # 超出退约次数：扣除权限（优先预约/特殊课程），若无可扣则取消验证
                if getattr(current_user, "priority_reservation", False):
                    current_user.priority_reservation = False
                elif getattr(current_user, "special_course_access", False):
                    current_user.special_course_access = False
                else:
                    current_user.is_verified = False
                await db.commit()

    service = ReservationService(db)
    success = await service.cancel_reservation(reservation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )
    return None


@router.post("/{reservation_id:int}/pay", response_model=Reservation)
async def pay_reservation(
    reservation_id: int,
    payload: ReservationPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """预约不再支持手动支付，统一由管理员确认使用记录后自动扣费。"""
    await get_reservation_in_current_project(db, reservation_id, project_ctx)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="预约不再支持手动支付，请在使用结束后由管理员确认使用记录并自动扣费",
    )


@router.post("/{reservation_id:int}/complete", response_model=Reservation)
async def complete_reservation(
    reservation_id: int,
    payload: ReservationCompletionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """实验完成填报（管理员）"""
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can complete reservations")

    reservation = await get_reservation_in_current_project(db, reservation_id, project_ctx)

    if reservation.cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已取消的预约不能完成填报")
    if reservation.tool_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="预约未关联仪器，不能完成填报")

    if current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools and reservation.tool_id not in managed_tools:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    now = datetime.now()
    scheduled_end = _to_naive_datetime(reservation.end)
    if scheduled_end and scheduled_end > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="预约尚未结束，不能完成填报")

    actual_start = payload.actual_start or reservation.actual_start or reservation.start
    actual_end = payload.actual_end or reservation.actual_end or reservation.end
    actual_start_naive = _to_naive_datetime(actual_start)
    actual_end_naive = _to_naive_datetime(actual_end)
    if not actual_start_naive or not actual_end_naive or actual_end_naive <= actual_start_naive:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="实际结束时间必须晚于实际开始时间")
    if actual_end_naive > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="实际结束时间不能晚于当前时间")

    reservation.actual_start = actual_start
    reservation.actual_end = actual_end
    if payload.completion_note is not None:
        reservation.completion_note = payload.completion_note

    reservation.completed_by_id = current_user.id
    reservation.completed_at = now
    try:
        await UsageEventService.upsert_from_completed_reservation(
            db,
            reservation,
            completed_by_id=current_user.id,
        )
        await db.commit()
        await db.refresh(reservation)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return reservation


@router.get("/export")
async def export_reservations(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """导出预约（CSV，仅管理员）"""
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can export reservations")

    service = ReservationService(db)
    reservations = await service.get_reservations(
        skip=0,
        limit=5000,
        project_id=project_ctx.project_id,
        start_date=start_date,
        end_date=end_date,
    )
    if current_user.is_staff and not current_user.is_superuser:
        managed_tools = getattr(current_user, "managed_tool_ids_list", []) or []
        if managed_tools:
            reservations = [r for r in reservations if r.tool_id in managed_tools]

    try:
        db.add(AuditLog(user_id=current_user.id, action="EXPORT_RESERVATIONS", detail="csv"))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()

    def generate():
        header = "id,tool,user,project,start,end,cancelled,paid,amount\\n"
        yield header
        for r in reservations:
            yield f"{r.id},{r.tool.name if r.tool else ''},{r.user.username if r.user else ''},{r.project.name if r.project else ''},{r.start},{r.end},{int(r.cancelled)},{r.payment_status},{r.payment_amount}\\n"

    return StreamingResponse(generate(), media_type="text/csv")
