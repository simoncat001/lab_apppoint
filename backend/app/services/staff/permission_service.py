"""Port of `PermissionServiceImpl`.

Reads from `staff_user_role`, `staff_role`, `staff_department_user`,
`staff_project_user`, `staff_group_user` to answer the standard role
questions the Spring service used to answer.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import (
    StaffDepartmentUser,
    StaffGroupUser,
    StaffProjectUser,
    StaffRole,
    StaffUserRole,
)

SUPER_ADMIN_ROLE_CODE = "SUPER_ADMIN"
MEMBER_TYPE_MEMBER = 0
MEMBER_TYPE_ADMIN = 1


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_super_admin(self, user_id: Optional[int]) -> bool:
        if not user_id:
            return False
        role_id_row = await self.db.execute(
            select(StaffRole.id).where(StaffRole.code == SUPER_ADMIN_ROLE_CODE)
        )
        super_role_id = role_id_row.scalar_one_or_none()
        if super_role_id is None:
            return False
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StaffUserRole)
                .where(StaffUserRole.user_id == user_id, StaffUserRole.role_id == super_role_id)
            )
        ).scalar_one()
        return int(count or 0) > 0

    async def is_dept_admin(self, user_id: Optional[int], dept_id: int) -> bool:
        if await self.is_super_admin(user_id):
            return True
        if not user_id:
            return False
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StaffDepartmentUser)
                .where(
                    StaffDepartmentUser.department_id == dept_id,
                    StaffDepartmentUser.user_id == user_id,
                    StaffDepartmentUser.type == MEMBER_TYPE_ADMIN,
                )
            )
        ).scalar_one()
        return int(count or 0) > 0

    async def is_dept_member(self, user_id: Optional[int], dept_id: int) -> bool:
        if await self.is_super_admin(user_id):
            return True
        if not user_id:
            return False
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StaffDepartmentUser)
                .where(
                    StaffDepartmentUser.department_id == dept_id,
                    StaffDepartmentUser.user_id == user_id,
                )
            )
        ).scalar_one()
        return int(count or 0) > 0

    async def is_project_admin(self, user_id: Optional[int], project_id: int) -> bool:
        if await self.is_super_admin(user_id):
            return True
        if not user_id:
            return False
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StaffProjectUser)
                .where(
                    StaffProjectUser.project_id == project_id,
                    StaffProjectUser.user_id == user_id,
                    StaffProjectUser.type == MEMBER_TYPE_ADMIN,
                )
            )
        ).scalar_one()
        return int(count or 0) > 0

    async def is_group_admin(self, user_id: Optional[int], group_id: int) -> bool:
        if await self.is_super_admin(user_id):
            return True
        if not user_id:
            return False
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(StaffGroupUser)
                .where(
                    StaffGroupUser.group_id == group_id,
                    StaffGroupUser.user_id == user_id,
                    StaffGroupUser.type == MEMBER_TYPE_ADMIN,
                )
            )
        ).scalar_one()
        return int(count or 0) > 0
