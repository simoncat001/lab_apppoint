"""Staff user endpoints — port of UserController."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.staff.deps import get_current_staff_user
from app.db.session import get_db
from app.models.staff import StaffUser
from app.schemas.staff.user import (
    StaffUserResponse,
    UserQuery,
    UserUpsertRequest,
)
from app.services.staff.result import StaffBusinessError, ok, paginated
from app.services.staff.user_service import StaffUserService

router = APIRouter()


def _serialise(user: StaffUser) -> dict:
    return StaffUserResponse.model_validate(user).model_dump(by_alias=True, exclude_none=True)


@router.post("")
async def save_user(
    payload: UserUpsertRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    service = StaffUserService(db)
    body = payload.model_dump(by_alias=False, exclude_none=True)
    body.pop("id", None)  # POST is a create — id MUST come from DB
    await service.create_user(actor_id=int(actor.id), payload=body)
    return ok(True)


@router.put("")
async def update_user(
    payload: UserUpsertRequest,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    service = StaffUserService(db)
    body = payload.model_dump(by_alias=False, exclude_none=True)
    await service.update_user(actor_id=int(actor.id), payload=body)
    return ok(True)


@router.delete("/{user_id}")
async def remove_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: StaffUser = Depends(get_current_staff_user),
):
    service = StaffUserService(db)
    deleted = await service.delete_user(actor_id=int(actor.id), target_id=user_id)
    if not deleted:
        raise StaffBusinessError("用户不存在", code=404)
    return ok(True)


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _actor: StaffUser = Depends(get_current_staff_user),
):
    service = StaffUserService(db)
    user = await service.get_user(user_id)
    if user is None:
        raise StaffBusinessError("用户不存在", code=404)
    return ok(_serialise(user))


@router.post("/list")
async def list_users(
    query: UserQuery,
    db: AsyncSession = Depends(get_db),
    _actor: StaffUser = Depends(get_current_staff_user),
):
    page_num, page_size, enabled = query.normalized_page()
    service = StaffUserService(db)
    rows, total = await service.list_users(
        keyword=query.keyword,
        page_num=page_num,
        page_size=page_size,
        enabled=enabled,
    )
    items = [_serialise(u) for u in rows]
    return paginated(items, page_num=page_num, page_size=page_size, total=total)
