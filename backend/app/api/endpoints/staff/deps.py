"""FastAPI dependencies used by the staff routers.

These replace Spring's `SecurityContextHolder` + `@PreAuthorize` plumbing.
"""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.staff_security import extract_staff_username
from app.db.session import get_db
from app.models.staff import StaffUser
from app.services.staff.permission_service import PermissionService
from app.services.staff.result import StaffBusinessError


async def get_current_staff_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> StaffUser:
    """Resolve the `staff_user` row identified by the bearer JWT."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise StaffBusinessError("未登录", code=401)
    token = authorization.split(None, 1)[1].strip()

    username = extract_staff_username(token)
    if not username:
        raise StaffBusinessError("登录已失效，请重新登录", code=401)

    user = (
        await db.execute(select(StaffUser).where(StaffUser.username == username))
    ).scalar_one_or_none()
    if user is None:
        raise StaffBusinessError("登录用户不存在", code=401)
    return user


async def require_super_admin(
    db: AsyncSession = Depends(get_db),
    user: StaffUser = Depends(get_current_staff_user),
) -> StaffUser:
    if not await PermissionService(db).is_super_admin(user.id):
        raise StaffBusinessError("无权限执行此操作")
    return user
