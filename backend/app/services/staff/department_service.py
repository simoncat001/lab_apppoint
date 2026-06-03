"""Port of `DepartmentServiceImpl`."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import (
    StaffDepartment,
    StaffDepartmentUser,
    StaffProject,
    StaffUser,
)
from app.services.staff.permission_service import (
    MEMBER_TYPE_ADMIN,
    MEMBER_TYPE_MEMBER,
    PermissionService,
)
from app.services.staff.result import StaffBusinessError


class StaffDepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permissions = PermissionService(db)

    async def list_visible(
        self,
        *,
        actor_id: int,
        keyword: Optional[str],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        base = select(StaffDepartment)
        if keyword:
            base = base.where(StaffDepartment.name.ilike(f"%{keyword}%"))
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        stmt = base.order_by(StaffDepartment.id.desc())
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)
        departments = (await self.db.execute(stmt)).scalars().all()
        if not departments:
            return [], int(total or 0)

        # Membership flags for the actor.
        memberships_rows = await self.db.execute(
            select(StaffDepartmentUser.department_id, StaffDepartmentUser.type)
            .where(StaffDepartmentUser.user_id == actor_id)
        )
        joined: set[int] = set()
        admin_in: set[int] = set()
        for dept_id, mtype in memberships_rows.all():
            joined.add(int(dept_id))
            if int(mtype or 0) == MEMBER_TYPE_ADMIN:
                admin_in.add(int(dept_id))

        is_super = await self.permissions.is_super_admin(actor_id)
        items: list[dict] = []
        for d in departments:
            items.append(
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "created_time": d.created_time,
                    "updated_time": d.updated_time,
                    "joined": is_super or (d.id in joined),
                    "can_manage": is_super or (d.id in admin_in),
                }
            )
        return items, int(total or 0)

    async def get_detail(self, *, actor_id: int, dept_id: int) -> dict:
        await self._check_visible(actor_id=actor_id, dept_id=dept_id)
        department = await self.db.get(StaffDepartment, dept_id)
        if department is None:
            raise StaffBusinessError("部门不存在")
        member_count = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(StaffDepartmentUser).where(
                        StaffDepartmentUser.department_id == dept_id
                    )
                )
            ).scalar_one()
            or 0
        )
        project_count = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(StaffProject).where(
                        StaffProject.department_id == dept_id
                    )
                )
            ).scalar_one()
            or 0
        )
        return {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "created_time": department.created_time,
            "member_count": member_count,
            "project_count": project_count,
        }

    async def create(self, *, actor_id: int, name: str, description: Optional[str]) -> StaffDepartment:
        if not await self.permissions.is_super_admin(actor_id):
            raise StaffBusinessError("无权限创建部门")
        if not name or not name.strip():
            raise StaffBusinessError("部门名称不能为空")
        if await self._name_exists(name):
            raise StaffBusinessError(f"部门名称 {name} 已存在")
        department = StaffDepartment(name=name.strip(), description=description)
        self.db.add(department)
        await self.db.commit()
        await self.db.refresh(department)
        return department

    async def update(self, *, actor_id: int, dept_id: int, name: str, description: Optional[str]) -> StaffDepartment:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限编辑部门")
        department = await self.db.get(StaffDepartment, dept_id)
        if department is None:
            raise StaffBusinessError("部门不存在")
        if await self._name_exists(name, exclude_id=dept_id):
            raise StaffBusinessError(f"部门名称 {name} 已存在")
        department.name = name
        department.description = description
        await self.db.commit()
        await self.db.refresh(department)
        return department

    async def delete(self, *, actor_id: int, dept_id: int) -> bool:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限删除部门")
        department = await self.db.get(StaffDepartment, dept_id)
        if department is None:
            return False
        await self.db.delete(department)
        await self.db.commit()
        return True

    async def add_members(self, *, actor_id: int, dept_id: int, user_ids: list[int]) -> bool:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限添加成员")
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")
        existing_rows = await self.db.execute(
            select(StaffDepartmentUser.user_id)
            .where(StaffDepartmentUser.department_id == dept_id)
            .where(StaffDepartmentUser.user_id.in_(user_ids))
        )
        existing = {int(r) for (r,) in existing_rows.all()}
        for uid in user_ids:
            if int(uid) in existing:
                continue
            self.db.add(
                StaffDepartmentUser(
                    department_id=dept_id,
                    user_id=int(uid),
                    type=MEMBER_TYPE_MEMBER,
                )
            )
        await self.db.commit()
        return True

    async def remove_members(self, *, actor_id: int, dept_id: int, user_ids: list[int]) -> bool:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限移除成员")
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")
        memberships = (
            await self.db.execute(
                select(StaffDepartmentUser).where(
                    StaffDepartmentUser.department_id == dept_id,
                    StaffDepartmentUser.user_id.in_(user_ids),
                )
            )
        ).scalars().all()
        for m in memberships:
            await self.db.delete(m)
        await self.db.commit()
        return True

    async def set_admin(self, *, actor_id: int, dept_id: int, user_id: int) -> bool:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限指定管理员")
        member = (
            await self.db.execute(
                select(StaffDepartmentUser).where(
                    StaffDepartmentUser.department_id == dept_id,
                    StaffDepartmentUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是部门成员，请先添加")
        member.type = MEMBER_TYPE_ADMIN
        await self.db.commit()
        return True

    async def remove_admin(self, *, actor_id: int, dept_id: int, user_id: int) -> bool:
        await self._check_admin(actor_id=actor_id, dept_id=dept_id, message="无权限取消管理员")
        member = (
            await self.db.execute(
                select(StaffDepartmentUser).where(
                    StaffDepartmentUser.department_id == dept_id,
                    StaffDepartmentUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是部门成员")
        if int(member.type or 0) != MEMBER_TYPE_ADMIN:
            raise StaffBusinessError("该用户不是管理员")
        member.type = MEMBER_TYPE_MEMBER
        await self.db.commit()
        return True

    async def get_members(
        self,
        *,
        actor_id: int,
        dept_id: int,
        keyword: Optional[str],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        if not await self.permissions.is_dept_member(actor_id, dept_id):
            raise StaffBusinessError("无权限查看部门成员")

        stmt = (
            select(
                StaffUser.id.label("user_id"),
                StaffUser.username,
                StaffUser.name,
                StaffUser.email,
                StaffUser.phone,
                StaffDepartmentUser.type.label("member_type"),
            )
            .join(StaffDepartmentUser, StaffDepartmentUser.user_id == StaffUser.id)
            .where(StaffDepartmentUser.department_id == dept_id)
        )
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(StaffUser.name.ilike(like), StaffUser.username.ilike(like)))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one() or 0)

        stmt = stmt.order_by(StaffDepartmentUser.type.desc(), StaffUser.id.asc())
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)

        rows = (await self.db.execute(stmt)).all()
        items = [
            {
                "user_id": int(r.user_id),
                "username": r.username,
                "name": r.name,
                "email": r.email,
                "phone": r.phone,
                "is_admin": int(r.member_type or 0) == MEMBER_TYPE_ADMIN,
            }
            for r in rows
        ]
        return items, total

    # -------------------------------------------------------------- guards
    async def _check_admin(self, *, actor_id: int, dept_id: int, message: str) -> None:
        if not await self.permissions.is_dept_admin(actor_id, dept_id):
            raise StaffBusinessError(message)

    async def _check_visible(self, *, actor_id: int, dept_id: int) -> None:
        # Spring lets dept admins or super admins see the detail page.
        # We follow the same rule and additionally allow members to see basic info.
        if not await self.permissions.is_dept_member(actor_id, dept_id) and not await self.permissions.is_super_admin(actor_id):
            raise StaffBusinessError("无权限查看详情")

    async def _name_exists(self, name: str, *, exclude_id: Optional[int] = None) -> bool:
        stmt = select(func.count()).select_from(StaffDepartment).where(StaffDepartment.name == name)
        if exclude_id is not None:
            stmt = stmt.where(StaffDepartment.id != exclude_id)
        return int((await self.db.execute(stmt)).scalar_one() or 0) > 0
