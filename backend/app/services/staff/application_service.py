"""Port of `ApplicationRequestServiceImpl` (apply + list + approve + reject).

Permission model matches Spring exactly:
- `auditOnly=true` returns every application the current user is allowed
  to approve (dept-admin / project-admin / group-admin / SUPER_ADMIN).
- A specific `targetId+targetType` query also requires admin perms on
  that target.
- Otherwise the list defaults to "my own applications".
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import (
    StaffApplicationRequest,
    StaffDepartment,
    StaffDepartmentUser,
    StaffGroup,
    StaffGroupUser,
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

TARGET_DEPARTMENT = 1
TARGET_PROJECT = 2
TARGET_GROUP = 3

STATUS_PENDING = 0
STATUS_APPROVED = 1
STATUS_REJECTED = 2


class StaffApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permissions = PermissionService(db)

    async def apply(
        self,
        *,
        user_id: int,
        target_type: int,
        target_id: int,
        reason: Optional[str],
    ) -> StaffApplicationRequest:
        if not user_id:
            raise StaffBusinessError("未登录")
        if target_type not in {TARGET_DEPARTMENT, TARGET_PROJECT, TARGET_GROUP}:
            raise StaffBusinessError("参数错误")

        # Cascade requirements: group needs project membership; project needs department membership.
        if target_type == TARGET_GROUP:
            group = await self.db.get(StaffGroup, target_id)
            if group is None:
                raise StaffBusinessError("小组不存在")
            in_project = await self._count(
                select(func.count()).select_from(StaffProjectUser).where(
                    StaffProjectUser.project_id == group.project_id,
                    StaffProjectUser.user_id == user_id,
                )
            )
            if in_project == 0:
                raise StaffBusinessError("必须先加入所属项目才能申请加入小组")
        elif target_type == TARGET_PROJECT:
            project = await self.db.get(StaffProject, target_id)
            if project is None:
                raise StaffBusinessError("项目不存在")
            in_dept = await self._count(
                select(func.count()).select_from(StaffDepartmentUser).where(
                    StaffDepartmentUser.department_id == project.department_id,
                    StaffDepartmentUser.user_id == user_id,
                )
            )
            if in_dept == 0:
                raise StaffBusinessError("必须先加入所属部门才能申请加入项目")

        # Already a member?
        if target_type == TARGET_DEPARTMENT:
            member_count = await self._count(
                select(func.count()).select_from(StaffDepartmentUser).where(
                    StaffDepartmentUser.department_id == target_id,
                    StaffDepartmentUser.user_id == user_id,
                )
            )
        elif target_type == TARGET_PROJECT:
            member_count = await self._count(
                select(func.count()).select_from(StaffProjectUser).where(
                    StaffProjectUser.project_id == target_id,
                    StaffProjectUser.user_id == user_id,
                )
            )
        else:
            member_count = await self._count(
                select(func.count()).select_from(StaffGroupUser).where(
                    StaffGroupUser.group_id == target_id,
                    StaffGroupUser.user_id == user_id,
                )
            )
        if member_count > 0:
            raise StaffBusinessError("您已是该组织成员")

        pending = await self._count(
            select(func.count()).select_from(StaffApplicationRequest).where(
                StaffApplicationRequest.user_id == user_id,
                StaffApplicationRequest.target_id == target_id,
                StaffApplicationRequest.target_type == target_type,
                StaffApplicationRequest.status == STATUS_PENDING,
            )
        )
        if pending > 0:
            raise StaffBusinessError("已有待审核申请")

        record = StaffApplicationRequest(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            status=STATUS_PENDING,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ------------------------------------------------------------ approve
    async def approve(self, *, actor_id: int, application_id: int) -> bool:
        await self._handle_audit(actor_id=actor_id, application_id=application_id, new_status=STATUS_APPROVED)
        return True

    async def reject(self, *, actor_id: int, application_id: int) -> bool:
        await self._handle_audit(actor_id=actor_id, application_id=application_id, new_status=STATUS_REJECTED)
        return True

    async def _handle_audit(self, *, actor_id: int, application_id: int, new_status: int) -> None:
        application = await self.db.get(StaffApplicationRequest, application_id)
        if application is None:
            raise StaffBusinessError("申请不存在")
        if int(application.status or 0) != STATUS_PENDING:
            raise StaffBusinessError("该申请已处理")
        if not await self._can_audit_target(actor_id=actor_id, target_type=application.target_type, target_id=application.target_id):
            raise StaffBusinessError("无权限审核")

        application.status = new_status
        application.approver_id = actor_id
        application.approve_result = new_status

        if new_status == STATUS_APPROVED:
            await self._auto_join_member(application)

        await self.db.commit()

    async def _auto_join_member(self, application: StaffApplicationRequest) -> None:
        target_type = int(application.target_type or 0)
        target_id = int(application.target_id)
        user_id = int(application.user_id)

        if target_type == TARGET_DEPARTMENT:
            self.db.add(StaffDepartmentUser(department_id=target_id, user_id=user_id, type=MEMBER_TYPE_MEMBER))
        elif target_type == TARGET_PROJECT:
            self.db.add(StaffProjectUser(project_id=target_id, user_id=user_id, type=MEMBER_TYPE_MEMBER))
        elif target_type == TARGET_GROUP:
            self.db.add(StaffGroupUser(group_id=target_id, user_id=user_id, type=MEMBER_TYPE_MEMBER))

    # --------------------------------------------------------------- list
    async def list_applications(
        self,
        *,
        actor_id: int,
        status: Optional[int],
        target_type: Optional[int],
        target_id: Optional[int],
        audit_only: bool,
        page_num: int,
        page_size: int,
        enabled: bool,
    ) -> Tuple[List[dict], int]:
        if not actor_id:
            raise StaffBusinessError("未登录")

        stmt = select(StaffApplicationRequest)
        if status is not None:
            stmt = stmt.where(StaffApplicationRequest.status == status)

        if audit_only:
            stmt = await self._apply_audit_scope(stmt=stmt, actor_id=actor_id, target_type=target_type, target_id=target_id)
        elif target_id is not None and target_type is not None:
            if not await self._can_audit_target(actor_id=actor_id, target_type=target_type, target_id=target_id):
                raise StaffBusinessError("无权限查看该组织的申请记录")
            stmt = stmt.where(
                StaffApplicationRequest.target_type == target_type,
                StaffApplicationRequest.target_id == target_id,
            )
        else:
            if target_type is not None:
                stmt = stmt.where(StaffApplicationRequest.target_type == target_type)
            if target_id is not None:
                stmt = stmt.where(StaffApplicationRequest.target_id == target_id)
            # Default: list MY applications.
            stmt = stmt.where(StaffApplicationRequest.user_id == actor_id)

        stmt = stmt.order_by(StaffApplicationRequest.created_time.desc())

        total = int((await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0)
        if enabled:
            stmt = stmt.offset((page_num - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).scalars().all()
        return await self._with_display_names(rows), total

    async def _apply_audit_scope(self, *, stmt, actor_id: int, target_type: Optional[int], target_id: Optional[int]):
        is_super = await self.permissions.is_super_admin(actor_id)
        if is_super:
            if target_type is not None:
                stmt = stmt.where(StaffApplicationRequest.target_type == target_type)
            if target_id is not None:
                stmt = stmt.where(StaffApplicationRequest.target_id == target_id)
            return stmt

        dept_admin_ids = await self._admin_department_ids(actor_id)
        project_admin_ids = await self._admin_project_ids(actor_id)
        group_admin_ids = await self._admin_group_ids(actor_id)

        dept_managed_project_ids = await self._project_ids_in_departments(dept_admin_ids)
        auditable_project_ids = set(project_admin_ids) | dept_managed_project_ids

        project_managed_group_ids = await self._group_ids_in_projects(project_admin_ids)
        auditable_group_ids = set(group_admin_ids) | project_managed_group_ids

        if target_type == TARGET_DEPARTMENT:
            if not dept_admin_ids:
                return stmt.where(StaffApplicationRequest.id == -1)
            stmt = stmt.where(
                StaffApplicationRequest.target_type == TARGET_DEPARTMENT,
                StaffApplicationRequest.target_id.in_(dept_admin_ids),
            )
            if target_id is not None:
                stmt = stmt.where(StaffApplicationRequest.target_id == target_id)
            return stmt
        if target_type == TARGET_PROJECT:
            if not auditable_project_ids:
                return stmt.where(StaffApplicationRequest.id == -1)
            stmt = stmt.where(
                StaffApplicationRequest.target_type == TARGET_PROJECT,
                StaffApplicationRequest.target_id.in_(auditable_project_ids),
            )
            if target_id is not None:
                stmt = stmt.where(StaffApplicationRequest.target_id == target_id)
            return stmt
        if target_type == TARGET_GROUP:
            if not auditable_group_ids:
                return stmt.where(StaffApplicationRequest.id == -1)
            stmt = stmt.where(
                StaffApplicationRequest.target_type == TARGET_GROUP,
                StaffApplicationRequest.target_id.in_(auditable_group_ids),
            )
            if target_id is not None:
                stmt = stmt.where(StaffApplicationRequest.target_id == target_id)
            return stmt

        if target_id is not None:
            stmt = stmt.where(StaffApplicationRequest.target_id == target_id)

        if not dept_admin_ids and not auditable_project_ids and not auditable_group_ids:
            return stmt.where(StaffApplicationRequest.id == -1)

        clauses = []
        if dept_admin_ids:
            clauses.append(
                and_(
                    StaffApplicationRequest.target_type == TARGET_DEPARTMENT,
                    StaffApplicationRequest.target_id.in_(dept_admin_ids),
                )
            )
        if auditable_project_ids:
            clauses.append(
                and_(
                    StaffApplicationRequest.target_type == TARGET_PROJECT,
                    StaffApplicationRequest.target_id.in_(auditable_project_ids),
                )
            )
        if auditable_group_ids:
            clauses.append(
                and_(
                    StaffApplicationRequest.target_type == TARGET_GROUP,
                    StaffApplicationRequest.target_id.in_(auditable_group_ids),
                )
            )
        if clauses:
            stmt = stmt.where(or_(*clauses))
        return stmt

    # ------------------------------------------------------------ helpers
    async def _can_audit_target(self, *, actor_id: int, target_type: Optional[int], target_id: Optional[int]) -> bool:
        if await self.permissions.is_super_admin(actor_id):
            return True
        if target_type is None or target_id is None:
            return False
        if target_type == TARGET_DEPARTMENT:
            return await self.permissions.is_dept_admin(actor_id, int(target_id))
        if target_type == TARGET_PROJECT:
            project = await self.db.get(StaffProject, int(target_id))
            if project is None:
                return False
            if project.department_id is not None and await self.permissions.is_dept_admin(actor_id, project.department_id):
                return True
            return await self.permissions.is_project_admin(actor_id, project.id)
        if target_type == TARGET_GROUP:
            group = await self.db.get(StaffGroup, int(target_id))
            if group is None:
                return False
            if await self.permissions.is_project_admin(actor_id, group.project_id):
                return True
            return await self.permissions.is_group_admin(actor_id, group.id)
        return False

    async def _admin_department_ids(self, actor_id: int) -> set[int]:
        rows = await self.db.execute(
            select(StaffDepartmentUser.department_id).where(
                StaffDepartmentUser.user_id == actor_id,
                StaffDepartmentUser.type == MEMBER_TYPE_ADMIN,
            )
        )
        return {int(r) for (r,) in rows.all()}

    async def _admin_project_ids(self, actor_id: int) -> set[int]:
        rows = await self.db.execute(
            select(StaffProjectUser.project_id).where(
                StaffProjectUser.user_id == actor_id,
                StaffProjectUser.type == MEMBER_TYPE_ADMIN,
            )
        )
        return {int(r) for (r,) in rows.all()}

    async def _admin_group_ids(self, actor_id: int) -> set[int]:
        rows = await self.db.execute(
            select(StaffGroupUser.group_id).where(
                StaffGroupUser.user_id == actor_id,
                StaffGroupUser.type == MEMBER_TYPE_ADMIN,
            )
        )
        return {int(r) for (r,) in rows.all()}

    async def _project_ids_in_departments(self, dept_ids: set[int]) -> set[int]:
        if not dept_ids:
            return set()
        rows = await self.db.execute(
            select(StaffProject.id).where(StaffProject.department_id.in_(dept_ids))
        )
        return {int(r) for (r,) in rows.all()}

    async def _group_ids_in_projects(self, project_ids: set[int]) -> set[int]:
        if not project_ids:
            return set()
        rows = await self.db.execute(
            select(StaffGroup.id).where(StaffGroup.project_id.in_(project_ids))
        )
        return {int(r) for (r,) in rows.all()}

    async def _with_display_names(self, applications: List[StaffApplicationRequest]) -> List[dict]:
        if not applications:
            return []
        user_ids = {int(a.user_id) for a in applications if a.user_id is not None}
        dept_ids = {int(a.target_id) for a in applications if int(a.target_type or 0) == TARGET_DEPARTMENT}
        project_ids = {int(a.target_id) for a in applications if int(a.target_type or 0) == TARGET_PROJECT}
        group_ids = {int(a.target_id) for a in applications if int(a.target_type or 0) == TARGET_GROUP}

        users = {
            int(u.id): u
            for u in (
                (await self.db.execute(select(StaffUser).where(StaffUser.id.in_(user_ids)))).scalars().all()
                if user_ids
                else []
            )
        }
        departments = {
            int(d.id): d
            for d in (
                (await self.db.execute(select(StaffDepartment).where(StaffDepartment.id.in_(dept_ids)))).scalars().all()
                if dept_ids
                else []
            )
        }
        projects = {
            int(p.id): p
            for p in (
                (await self.db.execute(select(StaffProject).where(StaffProject.id.in_(project_ids)))).scalars().all()
                if project_ids
                else []
            )
        }
        groups = {
            int(g.id): g
            for g in (
                (await self.db.execute(select(StaffGroup).where(StaffGroup.id.in_(group_ids)))).scalars().all()
                if group_ids
                else []
            )
        }

        items: list[dict] = []
        for a in applications:
            user = users.get(int(a.user_id)) if a.user_id is not None else None
            applicant_name: Optional[str] = None
            if user is not None:
                applicant_name = (user.name or "").strip() or user.username
            target_name: Optional[str] = None
            target_type = int(a.target_type or 0)
            target_id = int(a.target_id)
            if target_type == TARGET_DEPARTMENT:
                d = departments.get(target_id)
                target_name = d.name if d else None
            elif target_type == TARGET_PROJECT:
                p = projects.get(target_id)
                target_name = p.name if p else None
            elif target_type == TARGET_GROUP:
                g = groups.get(target_id)
                target_name = g.name if g else None

            items.append(
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "target_type": a.target_type,
                    "target_id": a.target_id,
                    "status": a.status,
                    "reason": a.reason,
                    "approver_id": a.approver_id,
                    "approve_result": a.approve_result,
                    "created_time": a.created_time,
                    "applicant_name": applicant_name,
                    "target_name": target_name,
                }
            )
        return items

    async def _count(self, stmt) -> int:
        return int((await self.db.execute(stmt)).scalar_one() or 0)
