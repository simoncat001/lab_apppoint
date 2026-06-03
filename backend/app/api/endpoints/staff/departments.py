"""Staff department endpoints — port of DepartmentController."""

from typing import List

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.staff.deps import get_current_staff_user
from app.db.session import get_db
from app.models.staff import StaffUser
from app.schemas.staff.department import (
    ApplicationRequestPayload,
    DepartmentQuery,
    DepartmentRequest,
    MemberQuery,
)
from app.services.staff.application_service import (
    TARGET_DEPARTMENT,
    StaffApplicationService,
)
from app.services.staff.department_service import StaffDepartmentService
from app.services.staff.result import ok, paginated

router = APIRouter()


@router.post("/list")
async def list_departments(
    query: DepartmentQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    service = StaffDepartmentService(db)
    items, total = await service.list_visible(
        actor_id=int(actor.id),
        keyword=query.keyword,
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


@router.get("/{dept_id}")
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    detail = await StaffDepartmentService(db).get_detail(actor_id=int(actor.id), dept_id=dept_id)
    return ok(_camel(detail))


@router.post("")
async def create_department(
    payload: DepartmentRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).create(
        actor_id=int(actor.id),
        name=payload.name,
        description=payload.description,
    )
    return ok(True)


@router.put("/{dept_id}")
async def update_department(
    dept_id: int,
    payload: DepartmentRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).update(
        actor_id=int(actor.id),
        dept_id=dept_id,
        name=payload.name,
        description=payload.description,
    )
    return ok(True)


@router.delete("/{dept_id}")
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).delete(actor_id=int(actor.id), dept_id=dept_id)
    return ok(True)


@router.post("/{dept_id}/members")
async def add_members(
    dept_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).add_members(
        actor_id=int(actor.id),
        dept_id=dept_id,
        user_ids=user_ids,
    )
    return ok(True)


@router.post("/{dept_id}/remove-members")
async def remove_members(
    dept_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).remove_members(
        actor_id=int(actor.id),
        dept_id=dept_id,
        user_ids=user_ids,
    )
    return ok(True)


@router.post("/{dept_id}/admin")
async def set_admin(
    dept_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).set_admin(
        actor_id=int(actor.id),
        dept_id=dept_id,
        user_id=user_id,
    )
    return ok(True)


@router.post("/{dept_id}/admin/cancel")
async def cancel_admin(
    dept_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffDepartmentService(db).remove_admin(
        actor_id=int(actor.id),
        dept_id=dept_id,
        user_id=user_id,
    )
    return ok(True)


@router.post("/{dept_id}/members/list")
async def list_department_members(
    dept_id: int,
    query: MemberQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffDepartmentService(db).get_members(
        actor_id=int(actor.id),
        dept_id=dept_id,
        keyword=query.keyword,
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


@router.post("/{dept_id}/apply")
async def apply_to_department(
    dept_id: int,
    payload: ApplicationRequestPayload | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    reason = payload.reason if payload is not None else None
    await StaffApplicationService(db).apply(
        user_id=int(actor.id),
        target_type=TARGET_DEPARTMENT,
        target_id=dept_id,
        reason=reason,
    )
    return ok(True)


# --------------------------------------------------------------- helpers


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _camel(d: dict) -> dict:
    """Recursively convert snake_case dict keys to camelCase."""
    out: dict = {}
    for k, v in d.items():
        ck = _to_camel(k)
        if isinstance(v, dict):
            out[ck] = _camel(v)
        else:
            out[ck] = v
    return out
