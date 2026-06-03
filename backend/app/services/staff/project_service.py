"""Port of `ProjectServiceImpl`."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import (
    StaffDepartmentUser,
    StaffGroup,
    StaffProject,
    StaffProjectUser,
    StaffUser,
)
from app.services.staff.permission_service import (
    MEMBER_TYPE_ADMIN,
    MEMBER_TYPE_MEMBER,
    PermissionService,
)
from app.services.staff.result import StaffBusinessError


def _normalize(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    stripped = name.strip()
    return stripped or None


class StaffProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permissions = PermissionService(db)

    # ---------------------------------------------------------------- list
    async def list_visible(
        self,
        *,
        actor_id: int,
        keyword: Optional[str],
        department_id: Optional[int],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        base = select(StaffProject)
        if department_id is not None:
            base = base.where(StaffProject.department_id == department_id)
        if keyword:
            base = base.where(StaffProject.name.ilike(f"%{keyword}%"))

        is_super = await self.permissions.is_super_admin(actor_id)
        if not is_super:
            # Collect the project ids the actor is allowed to see (project
            # member OR member of the owning department).
            proj_rows = (
                await self.db.execute(
                    select(StaffProjectUser.project_id, StaffProjectUser.type).where(
                        StaffProjectUser.user_id == actor_id
                    )
                )
            ).all()
            joined_project_ids = {int(r[0]) for r in proj_rows}
            admin_project_ids = {int(r[0]) for r in proj_rows if int(r[1] or 0) == MEMBER_TYPE_ADMIN}

            dept_rows = (
                await self.db.execute(
                    select(StaffDepartmentUser.department_id, StaffDepartmentUser.type).where(
                        StaffDepartmentUser.user_id == actor_id
                    )
                )
            ).all()
            joined_dept_ids = {int(r[0]) for r in dept_rows}
            admin_dept_ids = {int(r[0]) for r in dept_rows if int(r[1] or 0) == MEMBER_TYPE_ADMIN}

            visible_ids = set(joined_project_ids)
            if joined_dept_ids:
                dept_proj_rows = (
                    await self.db.execute(
                        select(StaffProject.id).where(
                            StaffProject.department_id.in_(joined_dept_ids)
                        )
                    )
                ).all()
                visible_ids.update(int(r[0]) for r in dept_proj_rows)

            if not visible_ids:
                return [], 0
            base = base.where(StaffProject.id.in_(visible_ids))
        else:
            joined_project_ids = set()
            admin_project_ids = set()
            admin_dept_ids = set()

        total = int(
            (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0
        )
        stmt = base.order_by(StaffProject.id.desc())
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)

        rows = (await self.db.execute(stmt)).scalars().all()
        items: list[dict] = []
        for p in rows:
            if is_super:
                joined = can_manage = can_set_admin = True
            else:
                can_set_admin = p.department_id in admin_dept_ids
                can_manage = can_set_admin or (p.id in admin_project_ids)
                joined = p.id in joined_project_ids
            items.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "department_id": p.department_id,
                    "leader_id": p.leader_id,
                    "status": p.status,
                    "external_visible": bool(p.external_visible),
                    "external_display_name": p.external_display_name,
                    "created_time": p.created_time,
                    "updated_time": p.updated_time,
                    "joined": joined,
                    "can_manage": can_manage,
                    "can_set_admin": can_set_admin,
                }
            )
        return items, total

    # ------------------------------------------------------------- detail
    async def get_detail(self, *, actor_id: int, project_id: int) -> dict:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")

        if not await self.permissions.is_super_admin(actor_id):
            is_dept_admin = await self.permissions.is_dept_admin(actor_id, project.department_id) if project.department_id else False
            is_member = await self._is_project_member(actor_id, project_id)
            if not (is_dept_admin or is_member):
                raise StaffBusinessError("无权限查看详情")

        member_count = await self._count(
            select(func.count()).select_from(StaffProjectUser).where(StaffProjectUser.project_id == project_id)
        )
        group_count = await self._count(
            select(func.count()).select_from(StaffGroup).where(StaffGroup.project_id == project_id)
        )
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "department_id": project.department_id,
            "leader_id": project.leader_id,
            "status": project.status,
            "external_visible": bool(project.external_visible),
            "external_display_name": project.external_display_name,
            "created_time": project.created_time,
            "member_count": member_count,
            "group_count": group_count,
        }

    # ---------------------------------------------------------- create/up
    async def create(
        self,
        *,
        actor_id: int,
        name: str,
        description: Optional[str],
        department_id: Optional[int],
        external_visible: Optional[bool],
        external_display_name: Optional[str],
    ) -> StaffProject:
        if department_id is None:
            raise StaffBusinessError("所属部门不能为空")
        if not await self.permissions.is_super_admin(actor_id) and not await self.permissions.is_dept_admin(actor_id, department_id):
            raise StaffBusinessError("无权限在此部门创建项目")

        if await self._exists_name_in_dept(department_id, name):
            raise StaffBusinessError(f"该部门下项目名称 {name} 已存在")

        normalised_display_name = _normalize(external_display_name)
        external_visible_value = bool(external_visible)
        self._validate_external_display(external_visible_value, normalised_display_name)

        project = StaffProject(
            name=name,
            description=description,
            department_id=department_id,
            leader_id=actor_id,
            status=1,
            external_visible=external_visible_value,
            external_display_name=normalised_display_name,
        )
        self.db.add(project)
        await self.db.flush()

        # Creator becomes admin of the new project.
        self.db.add(
            StaffProjectUser(project_id=project.id, user_id=actor_id, type=MEMBER_TYPE_ADMIN)
        )
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(
        self,
        *,
        actor_id: int,
        project_id: int,
        name: str,
        description: Optional[str],
        external_visible: Optional[bool],
        external_display_name: Optional[str],
    ) -> StaffProject:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_manage(actor_id=actor_id, project=project, message="无权限修改项目")
        if await self._exists_name_in_dept(project.department_id, name, exclude_id=project_id):
            raise StaffBusinessError(f"该部门下项目名称 {name} 已存在")

        project.name = name
        project.description = description
        if external_visible is not None:
            project.external_visible = bool(external_visible)
        if external_display_name is not None:
            project.external_display_name = _normalize(external_display_name)
        self._validate_external_display(bool(project.external_visible), project.external_display_name)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, *, actor_id: int, project_id: int) -> bool:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_manage(actor_id=actor_id, project=project, message="无权限删除项目")
        await self.db.delete(project)
        await self.db.commit()
        return True

    # ------------------------------------------------------------ members
    async def add_members(self, *, actor_id: int, project_id: int, user_ids: list[int]) -> bool:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_member_perm(actor_id=actor_id, project=project, message="无权限添加成员")
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")

        # Members must already belong to the project's department.
        valid_dept_users = {
            int(r[0])
            for r in (
                await self.db.execute(
                    select(StaffDepartmentUser.user_id).where(
                        StaffDepartmentUser.department_id == project.department_id,
                        StaffDepartmentUser.user_id.in_(user_ids),
                    )
                )
            ).all()
        }
        for uid in user_ids:
            if int(uid) not in valid_dept_users:
                raise StaffBusinessError(f"用户 ID {uid} 不是该项目所属部门的成员")

        existing = {
            int(r[0])
            for r in (
                await self.db.execute(
                    select(StaffProjectUser.user_id).where(
                        StaffProjectUser.project_id == project_id,
                        StaffProjectUser.user_id.in_(user_ids),
                    )
                )
            ).all()
        }
        for uid in user_ids:
            if int(uid) in existing:
                continue
            self.db.add(
                StaffProjectUser(project_id=project_id, user_id=int(uid), type=MEMBER_TYPE_MEMBER)
            )
        await self.db.commit()
        return True

    async def remove_members(self, *, actor_id: int, project_id: int, user_ids: list[int]) -> bool:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_member_perm(actor_id=actor_id, project=project, message="无权限移除成员")
        if not user_ids:
            raise StaffBusinessError("成员列表不能为空")
        memberships = (
            await self.db.execute(
                select(StaffProjectUser).where(
                    StaffProjectUser.project_id == project_id,
                    StaffProjectUser.user_id.in_(user_ids),
                )
            )
        ).scalars().all()
        for m in memberships:
            await self.db.delete(m)
        await self.db.commit()
        return True

    async def set_admin(self, *, actor_id: int, project_id: int, user_id: int) -> bool:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_admin_assignment(actor_id=actor_id, project=project, message="无权限指定管理员")
        member = (
            await self.db.execute(
                select(StaffProjectUser).where(
                    StaffProjectUser.project_id == project_id,
                    StaffProjectUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是项目成员，请先添加")
        member.type = MEMBER_TYPE_ADMIN
        await self.db.commit()
        return True

    async def remove_admin(self, *, actor_id: int, project_id: int, user_id: int) -> bool:
        project = await self.db.get(StaffProject, project_id)
        if project is None:
            raise StaffBusinessError("项目不存在")
        await self._check_admin_assignment(actor_id=actor_id, project=project, message="无权限取消管理员")
        member = (
            await self.db.execute(
                select(StaffProjectUser).where(
                    StaffProjectUser.project_id == project_id,
                    StaffProjectUser.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise StaffBusinessError("该用户不是项目成员")
        if int(member.type or 0) != MEMBER_TYPE_ADMIN:
            raise StaffBusinessError("该用户不是管理员")
        member.type = MEMBER_TYPE_MEMBER
        await self.db.commit()
        return True

    async def get_members(
        self,
        *,
        actor_id: int,
        project_id: int,
        keyword: Optional[str],
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        if not await self.permissions.is_super_admin(actor_id) and not await self._is_project_member(actor_id, project_id):
            raise StaffBusinessError("无权限查看项目成员")
        return await _list_org_members(
            db=self.db,
            join_table=StaffProjectUser,
            join_id_attr="project_id",
            id_value=project_id,
            keyword=keyword,
            page_num=page_num,
            page_size=page_size,
            enabled=enabled,
        )

    # ----------------------------------------------------- public display
    async def get_public_display_names(self) -> list[str]:
        rows = (
            await self.db.execute(
                select(StaffProject)
                .where(StaffProject.status == 1, StaffProject.external_visible.is_(True))
                .order_by(StaffProject.id.asc())
            )
        ).scalars().all()
        names: list[str] = []
        for p in rows:
            display = _normalize(p.external_display_name) or p.name
            if display:
                names.append(display)
        return names

    # --------------------------------------------------------------- util
    async def _count(self, stmt) -> int:
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def _is_project_member(self, user_id: int, project_id: int) -> bool:
        return (
            await self._count(
                select(func.count()).select_from(StaffProjectUser).where(
                    StaffProjectUser.project_id == project_id,
                    StaffProjectUser.user_id == user_id,
                )
            )
            > 0
        )

    async def _exists_name_in_dept(
        self, department_id: int, name: str, *, exclude_id: Optional[int] = None
    ) -> bool:
        stmt = select(func.count()).select_from(StaffProject).where(
            StaffProject.department_id == department_id, StaffProject.name == name
        )
        if exclude_id is not None:
            stmt = stmt.where(StaffProject.id != exclude_id)
        return await self._count(stmt) > 0

    async def _has_base_permission(self, actor_id: int, project: StaffProject) -> bool:
        if await self.permissions.is_super_admin(actor_id):
            return True
        if project.department_id and await self.permissions.is_dept_admin(actor_id, project.department_id):
            return True
        if await self.permissions.is_project_admin(actor_id, project.id):
            return True
        return False

    async def _check_manage(self, *, actor_id: int, project: StaffProject, message: str) -> None:
        if not await self._has_base_permission(actor_id, project):
            raise StaffBusinessError(message)

    async def _check_admin_assignment(self, *, actor_id: int, project: StaffProject, message: str) -> None:
        if await self.permissions.is_super_admin(actor_id):
            return
        if project.department_id and await self.permissions.is_dept_admin(actor_id, project.department_id):
            return
        raise StaffBusinessError(message)

    async def _check_member_perm(self, *, actor_id: int, project: StaffProject, message: str) -> None:
        if await self._has_base_permission(actor_id, project):
            return
        # Group admins of the project may also manage project members.
        group_ids = (
            await self.db.execute(
                select(StaffGroup.id).where(StaffGroup.project_id == project.id)
            )
        ).all()
        for (gid,) in group_ids:
            if await self.permissions.is_group_admin(actor_id, int(gid)):
                return
        raise StaffBusinessError(message)

    def _validate_external_display(self, external_visible: bool, normalised_display_name: Optional[str]) -> None:
        if external_visible and not normalised_display_name:
            raise StaffBusinessError("开启对外展示时必须填写对外展示名称")


# ---------------------------------------------------------------- helpers


async def _list_org_members(
    *,
    db: AsyncSession,
    join_table,
    join_id_attr: str,
    id_value: int,
    keyword: Optional[str],
    page_num: int,
    page_size: int,
    enabled: bool,
) -> Tuple[List[dict], int]:
    """Shared helper used by Project and Group services to list members."""
    join_id_col = getattr(join_table, join_id_attr)

    stmt = (
        select(
            StaffUser.id.label("user_id"),
            StaffUser.username,
            StaffUser.name,
            StaffUser.email,
            StaffUser.phone,
            join_table.type.label("member_type"),
        )
        .join(join_table, join_table.user_id == StaffUser.id)
        .where(join_id_col == id_value)
    )
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(StaffUser.name.ilike(like) | StaffUser.username.ilike(like))

    total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0)
    stmt = stmt.order_by(join_table.type.desc(), StaffUser.id.asc())
    if enabled:
        stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()
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
