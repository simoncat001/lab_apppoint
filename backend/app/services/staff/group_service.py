"""Port of `SysGroupServiceImpl`."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import (
    StaffDepartmentUser,
    StaffGroup,
    StaffGroupUser,
    StaffProject,
    StaffProjectUser,
)
from app.services.staff.permission_service import (
    MEMBER_TYPE_ADMIN,
    MEMBER_TYPE_MEMBER,
    PermissionService,
)
from app.services.staff.project_service import _list_org_members
from app.services.staff.result import StaffBusinessError


class StaffGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permissions = PermissionService(db)

    async def list_visible(
        self,
        *,
        actor_id: int,
        keyword: Optional[str],
        project_id: Optional[int],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        base = select(StaffGroup)
        if project_id is not None:
            base = base.where(StaffGroup.project_id == project_id)
        if keyword:
            base = base.where(StaffGroup.name.ilike(f"%{keyword}%"))

        is_super = await self.permissions.is_super_admin(actor_id)
        if not is_super:
            # Groups visible via: group membership, project membership, dept membership
            group_rows = (
                await self.db.execute(
                    select(StaffGroupUser.group_id, StaffGroupUser.type).where(
                        StaffGroupUser.user_id == actor_id
                    )
                )
            ).all()
            joined_group_ids = {int(r[0]) for r in group_rows}
            group_admin_ids = {int(r[0]) for r in group_rows if int(r[1] or 0) == MEMBER_TYPE_ADMIN}

            project_rows = (
                await self.db.execute(
                    select(StaffProjectUser.project_id, StaffProjectUser.type).where(
                        StaffProjectUser.user_id == actor_id
                    )
                )
            ).all()
            project_ids_of_user = {int(r[0]) for r in project_rows}
            project_admin_ids = {int(r[0]) for r in project_rows if int(r[1] or 0) == MEMBER_TYPE_ADMIN}

            visible_group_ids = set(joined_group_ids)
            if project_ids_of_user:
                proj_group_rows = (
                    await self.db.execute(
                        select(StaffGroup.id).where(StaffGroup.project_id.in_(project_ids_of_user))
                    )
                ).all()
                visible_group_ids.update(int(r[0]) for r in proj_group_rows)

            dept_rows = (
                await self.db.execute(
                    select(StaffDepartmentUser.department_id, StaffDepartmentUser.type).where(
                        StaffDepartmentUser.user_id == actor_id
                    )
                )
            ).all()
            dept_admin_ids = {int(r[0]) for r in dept_rows if int(r[1] or 0) == MEMBER_TYPE_ADMIN}
            dept_ids_of_user = {int(r[0]) for r in dept_rows}
            if dept_ids_of_user:
                dept_projects = (
                    await self.db.execute(
                        select(StaffProject.id).where(StaffProject.department_id.in_(dept_ids_of_user))
                    )
                ).all()
                dept_project_ids = {int(r[0]) for r in dept_projects}
                if dept_project_ids:
                    dept_group_rows = (
                        await self.db.execute(
                            select(StaffGroup.id).where(StaffGroup.project_id.in_(dept_project_ids))
                        )
                    ).all()
                    visible_group_ids.update(int(r[0]) for r in dept_group_rows)

            if not visible_group_ids:
                return [], 0
            base = base.where(StaffGroup.id.in_(visible_group_ids))
        else:
            joined_group_ids = set()
            group_admin_ids = set()
            project_admin_ids = set()
            dept_admin_ids = set()

        total = int((await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)

        stmt = base.order_by(StaffGroup.id.desc())
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)
        groups = (await self.db.execute(stmt)).scalars().all()
        if not groups:
            return [], total

        # Map project_id → department_id for permission flags.
        project_ids_in_page = {int(g.project_id) for g in groups if g.project_id}
        project_to_dept: dict[int, int] = {}
        if project_ids_in_page:
            rows = (
                await self.db.execute(
                    select(StaffProject.id, StaffProject.department_id).where(
                        StaffProject.id.in_(project_ids_in_page)
                    )
                )
            ).all()
            project_to_dept = {int(pid): int(did) if did is not None else None for pid, did in rows}

        items: list[dict] = []
        for g in groups:
            if is_super:
                joined = can_manage = can_set_admin = True
            else:
                is_project_admin = int(g.project_id or 0) in project_admin_ids
                dept_id_of_group = project_to_dept.get(int(g.project_id or 0))
                is_dept_admin = dept_id_of_group in dept_admin_ids if dept_id_of_group else False
                is_group_admin = int(g.id) in group_admin_ids
                can_set_admin = is_project_admin or is_dept_admin
                can_manage = can_set_admin or is_group_admin
                joined = int(g.id) in joined_group_ids
            items.append(
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "project_id": g.project_id,
                    "admin_id": g.admin_id,
                    "created_time": g.created_time,
                    "updated_time": g.updated_time,
                    "joined": joined,
                    "can_manage": can_manage,
                    "can_set_admin": can_set_admin,
                }
            )
        return items, total

    async def get_detail(self, *, actor_id: int, group_id: int) -> dict:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")

        if not await self.permissions.is_super_admin(actor_id):
            project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
            is_dept_admin = (
                await self.permissions.is_dept_admin(actor_id, project.department_id)
                if project and project.department_id is not None
                else False
            )
            is_project_admin = await self.permissions.is_project_admin(actor_id, group.project_id) if group.project_id else False
            is_group_member = await self._is_group_member(actor_id, group_id)
            if not (is_dept_admin or is_project_admin or is_group_member):
                raise StaffBusinessError("无权限查看详情")

        member_count = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(StaffGroupUser).where(StaffGroupUser.group_id == group_id)
                )
            ).scalar_one()
            or 0
        )
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "project_id": group.project_id,
            "admin_id": group.admin_id,
            "created_time": group.created_time,
            "member_count": member_count,
        }

    async def create(
        self,
        *,
        actor_id: int,
        name: str,
        description: Optional[str],
        project_id: Optional[int],
    ) -> StaffGroup:
        if project_id is None:
            raise StaffBusinessError("所属项目不能为空")
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        if not await self.permissions.is_super_admin(actor_id) and not await self.permissions.is_dept_admin(actor_id, project.department_id) and not await self.permissions.is_project_admin(actor_id, project.id):
            raise StaffBusinessError("无权限在此项目创建小组")
        if await self._name_exists_in_project(project_id, name):
            raise StaffBusinessError(f"该项目下小组名称 {name} 已存在")

        group = StaffGroup(
            name=name,
            description=description,
            project_id=project_id,
            admin_id=actor_id,
        )
        self.db.add(group)
        await self.db.flush()
        self.db.add(StaffGroupUser(group_id=group.id, user_id=actor_id, type=MEMBER_TYPE_ADMIN))
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def update(
        self,
        *,
        actor_id: int,
        group_id: int,
        name: str,
        description: Optional[str],
    ) -> StaffGroup:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=True, message="无权限修改小组"
        )
        if await self._name_exists_in_project(group.project_id, name, exclude_id=group_id):
            raise StaffBusinessError(f"该项目下小组名称 {name} 已存在")
        group.name = name
        group.description = description
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def delete(self, *, actor_id: int, group_id: int) -> bool:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=True, message="无权限删除此小组"
        )
        await self.db.delete(group)
        await self.db.commit()
        return True

    async def add_members(self, *, actor_id: int, group_id: int, user_ids: list[int]) -> bool:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=True, message="无权限添加成员"
        )
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")

        valid_project_users = {
            int(r[0])
            for r in (
                await self.db.execute(
                    select(StaffProjectUser.user_id).where(
                        StaffProjectUser.project_id == group.project_id,
                        StaffProjectUser.user_id.in_(user_ids),
                    )
                )
            ).all()
        }
        for uid in user_ids:
            if int(uid) not in valid_project_users:
                raise StaffBusinessError(f"用户 ID {uid} 不是该小组所属项目的成员")

        existing = {
            int(r[0])
            for r in (
                await self.db.execute(
                    select(StaffGroupUser.user_id).where(
                        StaffGroupUser.group_id == group_id,
                        StaffGroupUser.user_id.in_(user_ids),
                    )
                )
            ).all()
        }
        for uid in user_ids:
            if int(uid) in existing:
                continue
            self.db.add(StaffGroupUser(group_id=group_id, user_id=int(uid), type=MEMBER_TYPE_MEMBER))
        await self.db.commit()
        return True

    async def remove_members(self, *, actor_id: int, group_id: int, user_ids: list[int]) -> bool:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=True, message="无权限移除成员"
        )
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")
        memberships = (
            await self.db.execute(
                select(StaffGroupUser).where(
                    StaffGroupUser.group_id == group_id,
                    StaffGroupUser.user_id.in_(user_ids),
                )
            )
        ).scalars().all()
        for m in memberships:
            await self.db.delete(m)
        await self.db.commit()
        return True

    async def set_admin(self, *, actor_id: int, group_id: int, user_id: int) -> bool:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=False, message="无权限指定管理员"
        )
        member = (
            await self.db.execute(
                select(StaffGroupUser).where(
                    StaffGroupUser.group_id == group_id,
                    StaffGroupUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是小组成员，请先添加")
        member.type = MEMBER_TYPE_ADMIN
        await self.db.commit()
        return True

    async def remove_admin(self, *, actor_id: int, group_id: int, user_id: int) -> bool:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
        await self._check_permission(
            actor_id=actor_id, group=group, project=project, allow_group_admin=False, message="无权限取消管理员"
        )
        member = (
            await self.db.execute(
                select(StaffGroupUser).where(
                    StaffGroupUser.group_id == group_id,
                    StaffGroupUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是小组成员")
        if int(member.type or 0) != MEMBER_TYPE_ADMIN:
            raise StaffBusinessError("该用户不是管理员")
        member.type = MEMBER_TYPE_MEMBER
        await self.db.commit()
        return True

    async def get_members(
        self,
        *,
        actor_id: int,
        group_id: int,
        keyword: Optional[str],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        group = await self.db.get(StaffGroup, group_id)
        if group is None:
            raise StaffBusinessError("小组不存在")
        can_view = await self.permissions.is_super_admin(actor_id) or await self._is_group_member(actor_id, group_id)
        if not can_view:
            project = await self.db.get(StaffProject, group.project_id) if group.project_id else None
            if project and project.department_id is not None and await self.permissions.is_dept_admin(actor_id, project.department_id):
                can_view = True
            elif await self.permissions.is_project_admin(actor_id, group.project_id):
                can_view = True
        if not can_view:
            raise StaffBusinessError("无权限查看小组成员")

        return await _list_org_members(
            db=self.db,
            join_table=StaffGroupUser,
            join_id_attr="group_id",
            id_value=group_id,
            keyword=keyword,
            page_num=page_num,
            page_size=page_size,
            enabled=enabled,
        )

    # ----------------------------------------------------------- helpers
    async def _is_group_member(self, user_id: int, group_id: int) -> bool:
        count = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(StaffGroupUser).where(
                        StaffGroupUser.group_id == group_id,
                        StaffGroupUser.user_id == user_id,
                    )
                )
            ).scalar_one()
            or 0
        )
        return count > 0

    async def _name_exists_in_project(self, project_id: int, name: str, *, exclude_id: Optional[int] = None) -> bool:
        stmt = select(func.count()).select_from(StaffGroup).where(
            StaffGroup.project_id == project_id, StaffGroup.name == name
        )
        if exclude_id is not None:
            stmt = stmt.where(StaffGroup.id != exclude_id)
        return int((await self.db.execute(stmt)).scalar_one() or 0) > 0

    async def _check_permission(
        self,
        *,
        actor_id: int,
        group: StaffGroup,
        project: Optional[StaffProject],
        allow_group_admin: bool,
        message: str,
    ) -> None:
        if await self.permissions.is_super_admin(actor_id):
            return
        if project and project.department_id is not None and await self.permissions.is_dept_admin(actor_id, project.department_id):
            return
        if await self.permissions.is_project_admin(actor_id, group.project_id):
            return
        if allow_group_admin and await self.permissions.is_group_admin(actor_id, group.id):
            return
        raise StaffBusinessError(message)
