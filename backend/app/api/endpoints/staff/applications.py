"""Staff application-request endpoints — port of ApplicationController."""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.staff.deps import get_current_staff_user
from app.db.session import get_db
from app.models.staff import StaffUser
from app.schemas.staff.application import (
    ApplicationQuery,
    ApplicationSubmitRequest,
    ApproveRequest,
    RejectRequest,
)
from app.services.staff.application_service import StaffApplicationService
from app.services.staff.result import ok, paginated

router = APIRouter()


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _camel(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        ck = _to_camel(k)
        out[ck] = _camel(v) if isinstance(v, dict) else v
    return out


@router.post("/list")
async def list_applications(
    query: ApplicationQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffApplicationService(db).list_applications(
        actor_id=int(actor.id),
        status=query.status,
        target_type=query.target_type,
        target_id=query.target_id,
        audit_only=bool(query.audit_only),
        page_num=page_num,
        page_size=page_size,
        enabled=enabled,
    )
    return paginated(
        [_camel(item) for item in items],
        page_num=page_num,
        page_size=page_size,
        total=total,
    )


@router.post("")
async def submit_application(
    payload: ApplicationSubmitRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffApplicationService(db).apply(
        user_id=int(actor.id),
        target_type=int(payload.target_type),
        target_id=int(payload.target_id),
        reason=payload.reason,
    )
    return ok(True)


@router.post("/{application_id}/approve")
async def approve_application(
    application_id: int,
    payload: ApproveRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    _ = payload  # comment is currently informational only, mirrors Spring
    await StaffApplicationService(db).approve(actor_id=int(actor.id), application_id=application_id)
    return ok(True)


@router.post("/{application_id}/reject")
async def reject_application(
    application_id: int,
    payload: RejectRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    _ = payload  # reason currently informational only, mirrors Spring
    await StaffApplicationService(db).reject(actor_id=int(actor.id), application_id=application_id)
    return ok(True)
