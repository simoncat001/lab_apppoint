"""
Current project workspace context helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.bill import Bill
from app.models.configuration import Configuration, ConfigurationHistory, ConfigurationOption
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.tool import Tool
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.services.project_service import ProjectService
from app.services.security_server_auth_service import SecurityServerAuthService
from app.services.security_server_project_service import SecurityServerProjectService, SecurityServerProjectServiceError


@dataclass
class CurrentProjectContext:
    project_id: int
    project: Project


def _project_header_missing() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="X-Current-Project-Id header is required",
    )


async def _is_security_server_user_authorized_for_project(
    db: AsyncSession,
    current_user: User,
    project: Project,
) -> bool:
    if not SecurityServerProjectService.is_enabled():
        return False
    identifier = (getattr(project, "application_identifier", None) or "").strip()
    if not identifier.startswith("security-server:"):
        return False
    remote_part = identifier.split(":", 1)[1].strip()
    try:
        remote_id = int(remote_part)
    except Exception:
        return False

    username = str(getattr(current_user, "username", "") or "").strip()
    if not username:
        return False
    visible_ids: set[int] = set()

    token = SecurityServerAuthService.get_cached_user_token(username)
    if token:
        try:
            visible_ids = await SecurityServerProjectService.list_visible_project_ids_with_token(token)
        except SecurityServerProjectServiceError as exc:
            if exc.status_code == 401:
                SecurityServerAuthService.clear_cached_user_token(username)
        if visible_ids:
            return remote_id in visible_ids

    try:
        visible_ids = await SecurityServerProjectService.list_visible_project_ids_for_username_from_db(
            db,
            username,
        )
    except Exception:
        return False
    return remote_id in visible_ids


async def get_current_project_context(
    x_current_project_id: Optional[int] = Header(None, alias="X-Current-Project-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentProjectContext:
    if x_current_project_id is None:
        raise _project_header_missing()

    project = await db.get(Project, int(x_current_project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current project not found")
    if not getattr(project, "active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current project is inactive")

    auth_source = (getattr(current_user, "auth_source", None) or "local").lower()
    if current_user.is_staff or current_user.is_superuser:
        return CurrentProjectContext(project_id=project.id, project=project)
    if auth_source == "security_server":
        if await _is_security_server_user_authorized_for_project(db, current_user, project):
            return CurrentProjectContext(project_id=project.id, project=project)
        # Fallback: local project access approvals are authoritative for external access
        # and should continue to work even if auth_source was marked as security_server.
        has_local_access = await ProjectService(db).user_has_project_access(current_user.id, project.id)
        if has_local_access:
            return CurrentProjectContext(project_id=project.id, project=project)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access the current project",
        )

    has_access = await ProjectService(db).user_has_project_access(current_user.id, project.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access the current project",
        )

    return CurrentProjectContext(project_id=project.id, project=project)


def ensure_project_id_matches_current_project(
    resource_project_id: Optional[int],
    ctx: CurrentProjectContext,
    *,
    detail_prefix: str = "Resource",
) -> None:
    if resource_project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{detail_prefix} is not bound to a project",
        )
    if int(resource_project_id) != int(ctx.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{detail_prefix} does not belong to the current project",
        )


async def get_tool_in_current_project(
    db: AsyncSession,
    tool_id: int,
    ctx: CurrentProjectContext,
) -> Tool:
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    ensure_project_id_matches_current_project(tool.project_id, ctx, detail_prefix="Tool")
    return tool


async def get_reservation_in_current_project(
    db: AsyncSession,
    reservation_id: int,
    ctx: CurrentProjectContext,
) -> Reservation:
    result = await db.execute(
        select(Reservation)
        .options(
            joinedload(Reservation.user),
            joinedload(Reservation.tool),
            joinedload(Reservation.project),
        )
        .where(Reservation.id == reservation_id)
    )
    reservation = result.scalars().first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    ensure_project_id_matches_current_project(reservation.project_id, ctx, detail_prefix="Reservation")
    return reservation


async def get_usage_event_in_current_project(
    db: AsyncSession,
    event_id: int,
    ctx: CurrentProjectContext,
) -> UsageEvent:
    result = await db.execute(
        select(UsageEvent)
        .options(
            joinedload(UsageEvent.user),
            joinedload(UsageEvent.operator),
            joinedload(UsageEvent.tool),
            joinedload(UsageEvent.project),
        )
        .where(UsageEvent.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage event not found")
    ensure_project_id_matches_current_project(event.project_id, ctx, detail_prefix="Usage event")
    return event


async def get_bill_in_current_project(
    db: AsyncSession,
    bill_id: int,
    ctx: CurrentProjectContext,
) -> Bill:
    bill = await db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if ctx.project.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current project is not bound to an account",
        )
    if int(bill.account_id) != int(ctx.project.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bill does not belong to the current project",
        )
    return bill


async def get_configuration_in_current_project(
    db: AsyncSession,
    configuration_id: int,
    ctx: CurrentProjectContext,
) -> Configuration:
    result = await db.execute(
        select(Configuration)
        .options(joinedload(Configuration.tool))
        .where(Configuration.id == configuration_id)
    )
    configuration = result.scalars().first()
    if not configuration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    tool = configuration.tool
    if tool is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configuration tool is missing")
    ensure_project_id_matches_current_project(tool.project_id, ctx, detail_prefix="Configuration")
    return configuration


async def get_configuration_option_in_current_project(
    db: AsyncSession,
    option_id: int,
    ctx: CurrentProjectContext,
) -> ConfigurationOption:
    result = await db.execute(
        select(ConfigurationOption)
        .options(
            joinedload(ConfigurationOption.configuration).joinedload(Configuration.tool),
            joinedload(ConfigurationOption.reservation),
        )
        .where(ConfigurationOption.id == option_id)
    )
    option = result.scalars().first()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration option not found")

    project_id = None
    if option.reservation is not None:
        project_id = option.reservation.project_id
    elif option.configuration is not None and option.configuration.tool is not None:
        project_id = option.configuration.tool.project_id

    ensure_project_id_matches_current_project(project_id, ctx, detail_prefix="Configuration option")
    return option


async def get_configuration_history_in_current_project(
    db: AsyncSession,
    history_id: int,
    ctx: CurrentProjectContext,
) -> ConfigurationHistory:
    result = await db.execute(
        select(ConfigurationHistory)
        .options(
            joinedload(ConfigurationHistory.configuration).joinedload(Configuration.tool),
            joinedload(ConfigurationHistory.user),
        )
        .where(ConfigurationHistory.id == history_id)
    )
    history = result.scalars().first()
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration history not found")

    project_id = None
    if history.configuration is not None and history.configuration.tool is not None:
        project_id = history.configuration.tool.project_id
    ensure_project_id_matches_current_project(project_id, ctx, detail_prefix="Configuration history")
    return history
