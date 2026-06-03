"""Staff project endpoints — port of ProjectController."""

from typing import List

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.staff.deps import get_current_staff_user
from app.db.session import get_db
from app.models.staff import StaffUser
from app.schemas.staff.department import ApplicationRequestPayload, MemberQuery
from app.schemas.staff.project import ProjectQuery, ProjectRequest
from app.services.staff.application_service import (
    TARGET_PROJECT,
    StaffApplicationService,
)
from app.services.staff.project_service import StaffProjectService
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
async def list_projects(
    query: ProjectQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffProjectService(db).list_visible(
        actor_id=int(actor.id),
        keyword=query.keyword,
        department_id=query.department_id,
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


@router.get("/public/display-names")
async def public_display_names(db: AsyncSession = Depends(get_db)):
    """Replicates `GET /api/projects/public/display-names` — no auth required."""
    names = await StaffProjectService(db).get_public_display_names()
    return ok(names)


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    detail = await StaffProjectService(db).get_detail(actor_id=int(actor.id), project_id=project_id)
    return ok(_camel(detail))


@router.post("")
async def create_project(
    payload: ProjectRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).create(
        actor_id=int(actor.id),
        name=payload.name,
        description=payload.description,
        department_id=payload.department_id,
        external_visible=payload.external_visible,
        external_display_name=payload.external_display_name,
    )
    return ok(True)


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    payload: ProjectRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).update(
        actor_id=int(actor.id),
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        external_visible=payload.external_visible,
        external_display_name=payload.external_display_name,
    )
    return ok(True)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).delete(actor_id=int(actor.id), project_id=project_id)
    return ok(True)


@router.post("/{project_id}/members")
async def add_members(
    project_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).add_members(
        actor_id=int(actor.id), project_id=project_id, user_ids=user_ids
    )
    return ok(True)


@router.post("/{project_id}/remove-members")
async def remove_members(
    project_id: int,
    user_ids: List[int] = Body(default_factory=list),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).remove_members(
        actor_id=int(actor.id), project_id=project_id, user_ids=user_ids
    )
    return ok(True)


@router.post("/{project_id}/admin")
async def set_admin(
    project_id: int,
    user_id: int = Query(..., alias="userId"),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).set_admin(
        actor_id=int(actor.id), project_id=project_id, user_id=user_id
    )
    return ok(True)


@router.post("/{project_id}/admin/cancel")
async def cancel_admin(
    project_id: int,
    user_id: int = Query(..., alias="userId"),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    await StaffProjectService(db).remove_admin(
        actor_id=int(actor.id), project_id=project_id, user_id=user_id
    )
    return ok(True)


@router.post("/{project_id}/members/list")
async def list_project_members(
    project_id: int,
    query: MemberQuery,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    items, total = await StaffProjectService(db).get_members(
        actor_id=int(actor.id),
        project_id=project_id,
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


@router.post("/{project_id}/apply")
async def apply_to_project(
    project_id: int,
    payload: ApplicationRequestPayload | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    reason = payload.reason if payload is not None else None
    await StaffApplicationService(db).apply(
        user_id=int(actor.id),
        target_type=TARGET_PROJECT,
        target_id=project_id,
        reason=reason,
    )
    return ok(True)
