from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.models.reservation import Reservation
from app.models.tool import Tool
from app.models.usage_event import UsageEvent
from app.models.audit_log import AuditLog
from app.schemas.report import ProjectReportSummary

router = APIRouter()


def _date_filters(start_date: Optional[datetime], end_date: Optional[datetime], column):
    filters = []
    if start_date is not None:
        filters.append(column >= start_date)
    if end_date is not None:
        filters.append(column <= end_date)
    return filters


@router.get("/users")
async def user_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can view reports")

    scoped_user_ids = (
        select(Reservation.user_id)
        .where(
            Reservation.project_id == project_ctx.project_id,
            *_date_filters(start_date, end_date, Reservation.start),
        )
        .distinct()
    )

    total_result = await db.execute(select(func.count(User.id)).where(User.id.in_(scoped_user_ids)))
    total = total_result.scalar_one()
    active_result = await db.execute(
        select(func.count(User.id)).where(
            User.id.in_(scoped_user_ids),
            User.is_active == True,
        )
    )
    active = active_result.scalar_one()
    new_result = await db.execute(
        select(func.count(User.id)).where(
            User.id.in_(scoped_user_ids),
            *_date_filters(start_date, end_date, User.date_joined),
        )
    )
    new_count = new_result.scalar_one()
    login_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.user_id.in_(scoped_user_ids),
            AuditLog.action == "LOGIN",
            *_date_filters(start_date, end_date, AuditLog.created_at),
        )
    )
    login_count = login_result.scalar_one()
    export_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.user_id.in_(scoped_user_ids),
            AuditLog.action == "EXPORT_RESERVATIONS",
            *_date_filters(start_date, end_date, AuditLog.created_at),
        )
    )
    export_count = export_result.scalar_one()
    return {
        "total": total,
        "active": active,
        "new_count": new_count,
        "login_count": login_count,
        "export_count": export_count,
    }


@router.get("/reservations")
async def reservation_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can view reports")

    base_filters = [
        Reservation.project_id == project_ctx.project_id,
        *_date_filters(start_date, end_date, Reservation.start),
    ]
    total_result = await db.execute(select(func.count(Reservation.id)).where(*base_filters))
    total = total_result.scalar_one()
    cancelled_result = await db.execute(
        select(func.count(Reservation.id)).where(*base_filters, Reservation.cancelled == True)
    )
    cancelled = cancelled_result.scalar_one()
    paid_result = await db.execute(
        select(func.count(UsageEvent.id)).where(
            UsageEvent.project_id == project_ctx.project_id,
            *_date_filters(start_date, end_date, UsageEvent.end),
            UsageEvent.validated == True,
            UsageEvent.waived == False,
            UsageEvent.end != None,
        )
    )
    paid = paid_result.scalar_one()
    return {
        "total": total,
        "cancelled": cancelled,
        "paid": paid,
    }


@router.get("/tools")
async def tool_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can view reports")

    total_result = await db.execute(select(func.count(Tool.id)).where(Tool.project_id == project_ctx.project_id))
    total = total_result.scalar_one()
    usage_result = await db.execute(
        select(Reservation.tool_id, func.count(Reservation.id))
        .where(
            Reservation.project_id == project_ctx.project_id,
            *_date_filters(start_date, end_date, Reservation.start),
        )
        .group_by(Reservation.tool_id)
    )
    usage = {tool_id: count for tool_id, count in usage_result.all()}
    return {
        "total": total,
        "usage_by_tool": usage,
    }


@router.get("/projects", response_model=ProjectReportSummary)
async def project_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can view reports")

    project = project_ctx.project
    report = {
        "project_id": int(project.id),
        "project_name": project.name,
        "external_display_name": project.external_display_name,
        "active": bool(project.active),
        "tool_count": 0,
        "active_tool_count": 0,
        "idle_tool_count": 0,
        "reservation_count": 0,
        "cancelled_reservation_count": 0,
        "paid_usage_count": 0,
        "top_tools": [],
    }

    tool_count_result = await db.execute(
        select(func.count(Tool.id)).where(Tool.project_id == project_ctx.project_id)
    )
    report["tool_count"] = int(tool_count_result.scalar_one() or 0)

    reservation_filters = [
        Reservation.project_id == project_ctx.project_id,
        *_date_filters(start_date, end_date, Reservation.start),
    ]
    reservation_counts_result = await db.execute(
        select(
            func.count(Reservation.id),
            func.sum(case((Reservation.cancelled == True, 1), else_=0)),
        ).where(*reservation_filters)
    )
    reservation_total, cancelled_total = reservation_counts_result.one()
    report["reservation_count"] = int(reservation_total or 0)
    report["cancelled_reservation_count"] = int(cancelled_total or 0)

    active_tool_count_result = await db.execute(
        select(func.count(func.distinct(Reservation.tool_id))).where(
            *reservation_filters,
            Reservation.tool_id != None,
        )
    )
    report["active_tool_count"] = int(active_tool_count_result.scalar_one() or 0)
    report["idle_tool_count"] = max(0, int(report["tool_count"]) - int(report["active_tool_count"]))

    paid_usage_result = await db.execute(
        select(func.count(UsageEvent.id)).where(
            UsageEvent.project_id == project_ctx.project_id,
            *_date_filters(start_date, end_date, UsageEvent.end),
            UsageEvent.validated == True,
            UsageEvent.waived == False,
            UsageEvent.end != None,
        )
    )
    report["paid_usage_count"] = int(paid_usage_result.scalar_one() or 0)

    top_tools_result = await db.execute(
        select(
            Tool.id,
            Tool.name,
            func.count(Reservation.id),
        )
        .join(Tool, Reservation.tool_id == Tool.id)
        .where(
            *reservation_filters,
            Reservation.tool_id != None,
        )
        .group_by(Tool.id, Tool.name)
    )
    global_top_tools: list[dict[str, int | str | None]] = []
    for tool_id, tool_name, reservation_count in top_tools_result.all():
        if tool_id is None:
            continue
        row = {
            "tool_id": int(tool_id),
            "tool_name": tool_name,
            "reservation_count": int(reservation_count or 0),
        }
        global_top_tools.append(
            {
                **row,
                "project_id": int(project.id),
                "project_name": project.external_display_name or project.name,
            }
        )

    top_tools = sorted(
        global_top_tools,
        key=lambda item: (-int(item["reservation_count"]), str(item["tool_name"]).lower()),
    )
    report["top_tools"] = top_tools[:3]

    return {
        "total_projects": 1,
        "active_projects": 1 if project.active else 0,
        "inactive_projects": 0 if project.active else 1,
        "uncategorized_tools": 0,
        "project_reports": [report],
        "top_tools": top_tools[:10],
    }


#
# NOTE: Consumables module removed.
#
