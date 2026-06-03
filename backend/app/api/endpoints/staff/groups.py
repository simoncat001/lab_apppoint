"""Staff group endpoints — port of GroupController."""

from typing import List

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.staff.deps import get_current_staff_user
from app.db.session import get_db
from app.models.staff import StaffUser
from app.schemas.staff.department import ApplicationRequestPayload, MemberQuery
from app.schemas.staff.group import GroupQuery, GroupRequest
from app.services.staff.application_service import (
    TARGET_GROUP,
    StaffApplicationService,
)
from app.services.staff.group_service import StaffGroupService
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
async def list_groups(
    query: GroupQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffGroupService(db).list_visible(
        actor_id=int(actor.id),
        keyword=query.keyword,
        project_id=query.project_id,
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


@router.get("/{group_id}")
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    detail = await StaffGroupService(db).get_detail(actor_id=int(actor.id), group_id=group_id)
    return ok(_camel(detail))


@router.post("")
async def create_group(
    payload: GroupRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).create(
        actor_id=int(actor.id),
        name=payload.name,
        description=payload.description,
        project_id=payload.project_id,
    )
    return ok(True)


@router.put("/{group_id}")
async def update_group(
    group_id: int,
    payload: GroupRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).update(
        actor_id=int(actor.id),
        group_id=group_id,
        name=payload.name,
        description=payload.description,
    )
    return ok(True)


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).delete(actor_id=int(actor.id), group_id=group_id)
    return ok(True)


@router.post("/{group_id}/members")
async def add_members(
    group_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).add_members(
        actor_id=int(actor.id), group_id=group_id, user_ids=user_ids
    )
    return ok(True)


@router.post("/{group_id}/remove-members")
async def remove_members(
    group_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).remove_members(
        actor_id=int(actor.id), group_id=group_id, user_ids=user_ids
    )
    return ok(True)


@router.post("/{group_id}/admin")
async def set_admin(
    group_id: int,
    user_id: int = Query(..., alias="userId"),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).set_admin(
        actor_id=int(actor.id), group_id=group_id, user_id=user_id
    )
    return ok(True)


@router.post("/{group_id}/admin/cancel")
async def cancel_admin(
    group_id: int,
    user_id: int = Query(..., alias="userId"),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffGroupService(db).remove_admin(
        actor_id=int(actor.id), group_id=group_id, user_id=user_id
    )
    return ok(True)


@router.post("/{group_id}/members/list")
async def list_group_members(
    group_id: int,
    query: MemberQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffGroupService(db).get_members(
        actor_id=int(actor.id),
        group_id=group_id,
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


@router.post("/{group_id}/apply")
async def apply_to_group(
    group_id: int,
    payload: ApplicationRequestPayload | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    reason = payload.reason if payload is not None else None
    await StaffApplicationService(db).apply(
        user_id=int(actor.id),
        target_type=TARGET_GROUP,
        target_id=group_id,
        reason=reason,
    )
    return ok(True)
