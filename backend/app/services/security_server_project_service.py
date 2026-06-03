"""Internal-employee project sync service (legacy name preserved).

Like its sibling auth-service module, this used to call the standalone
Spring `security-server` over HTTP. It now reads the `staff_*` tables in
the same database and reuses the in-process `StaffProjectService`. All
public API surface (method names, exceptions, dataclasses) is preserved
so the rest of the codebase keeps working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Any, NamedTuple, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.staff_security import extract_staff_username
from app.db.session import AsyncSessionLocal
from app.models.staff import (
    StaffDepartmentUser,
    StaffGroupUser,
    StaffProject,
    StaffProjectUser,
    StaffRole,
    StaffUser,
    StaffUserRole,
)


@dataclass
class SecurityServerProjectRecord:
    remote_id: int
    name: str
    active: bool
    created_at: Optional[datetime] = None
    external_visible: Optional[bool] = None
    external_display_name: Optional[str] = None


class SecurityServerProjectServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SecurityServerPermissionSnapshot(NamedTuple):
    is_super_admin: bool
    is_admin: bool


# Cache used by `list_visible_project_ids_with_token`. The legacy
# implementation keyed by raw remote token; we keep the same shape so
# existing call sites can re-use the result identically.
_token_project_ids_cache: dict[str, tuple[float, set[int]]] = {}


def _project_to_record(project: StaffProject) -> SecurityServerProjectRecord:
    return SecurityServerProjectRecord(
        remote_id=int(project.id),
        name=project.name or "",
        active=int(project.status or 0) == 1,
        created_at=project.created_time,
        external_visible=bool(project.external_visible) if project.external_visible is not None else None,
        external_display_name=project.external_display_name,
    )


def _project_to_dto(project: StaffProject) -> dict[str, Any]:
    """Mirror Spring's Project entity JSON (camelCase, ISO timestamps)."""
    return {
        "id": int(project.id) if project.id is not None else None,
        "name": project.name,
        "description": project.description,
        "departmentId": project.department_id,
        "leaderId": project.leader_id,
        "status": project.status,
        "externalVisible": bool(project.external_visible) if project.external_visible is not None else False,
        "externalDisplayName": project.external_display_name,
        "createdTime": project.created_time.isoformat() if project.created_time else None,
        "updatedTime": project.updated_time.isoformat() if project.updated_time else None,
    }


async def _resolve_staff_user_id(session: AsyncSession, username: str) -> Optional[int]:
    username_normalized = (username or "").strip()
    if not username_normalized:
        return None
    row = await session.execute(
        select(StaffUser.id).where(
            StaffUser.username == username_normalized,
            StaffUser.status == 1,
        )
    )
    value = row.scalar_one_or_none()
    return int(value) if value is not None else None


async def _list_visible_project_ids_for_user_id(session: AsyncSession, staff_user_id: int) -> set[int]:
    """Visible == direct project member OR member of the owning department."""
    direct_rows = await session.execute(
        select(StaffProjectUser.project_id).where(StaffProjectUser.user_id == staff_user_id)
    )
    direct_ids: set[int] = {int(r) for (r,) in direct_rows.all()}

    dept_rows = await session.execute(
        select(StaffDepartmentUser.department_id).where(StaffDepartmentUser.user_id == staff_user_id)
    )
    dept_ids = {int(r) for (r,) in dept_rows.all()}

    if dept_ids:
        proj_rows = await session.execute(
            select(StaffProject.id).where(StaffProject.department_id.in_(dept_ids))
        )
        for (pid,) in proj_rows.all():
            direct_ids.add(int(pid))

    if not direct_ids:
        return set()

    active_rows = await session.execute(
        select(StaffProject.id).where(
            StaffProject.id.in_(direct_ids),
            or_(StaffProject.status.is_(None), StaffProject.status == 1),
        )
    )
    return {int(r) for (r,) in active_rows.all()}


class SecurityServerProjectService:
    """In-process replacement for the old HTTP project client."""

    # Kept on the class so existing tests / code that monkey-patches the
    # attribute continues to work.
    _token_project_ids_cache = _token_project_ids_cache

    # ----------------------------------------------------------- feature
    @staticmethod
    def is_enabled() -> bool:
        # The legacy implementation gated on `SECURITY_SERVER_PROJECT_SYNC_ENABLED`
        # AND on the remote URL being configured. Now that everything is
        # in-process we honour the same env switch (ops can disable the
        # integration), but no remote URL is required.
        return bool(
            settings.SECURITY_SERVER_PROJECT_SYNC_ENABLED
            and settings.SECURITY_SERVER_ENABLED
        )

    # ------------------------------------------------------ list/visible
    @staticmethod
    async def list_visible_projects() -> list[SecurityServerProjectRecord]:
        """Return every active staff project (service-account scope).

        Spring used the SERVICE account's token here, which is super-admin,
        so the visible set is "all active projects".
        """
        if not SecurityServerProjectService.is_enabled():
            return []
        try:
            async with AsyncSessionLocal() as session:
                rows = (
                    await session.execute(
                        select(StaffProject)
                        .where(or_(StaffProject.status.is_(None), StaffProject.status == 1))
                        .order_by(StaffProject.id.asc())
                    )
                ).scalars().all()
        except SQLAlchemyError as exc:
            raise SecurityServerProjectServiceError(
                "Staff project DB is unavailable", status_code=502
            ) from exc
        return [_project_to_record(p) for p in rows]

    @staticmethod
    async def list_visible_project_ids_with_token(
        token: str,
        *,
        cache_ttl_seconds: int = 60,
    ) -> set[int]:
        """Resolve the visible project ids for the user that owns `token`.

        With in-process auth we can extract the staff username straight
        from the JWT — no extra round trip needed.
        """
        normalized_token = (token or "").strip()
        if not normalized_token:
            return set()

        now = time.monotonic()
        cache_row = _token_project_ids_cache.get(normalized_token)
        if cache_row:
            expires_at, cached_ids = cache_row
            if now < expires_at:
                return set(cached_ids)

        username = extract_staff_username(normalized_token)
        if not username:
            return set()

        try:
            async with AsyncSessionLocal() as session:
                staff_user_id = await _resolve_staff_user_id(session, username)
                if staff_user_id is None:
                    ids: set[int] = set()
                else:
                    ids = await _list_visible_project_ids_for_user_id(session, staff_user_id)
        except SQLAlchemyError as exc:
            raise SecurityServerProjectServiceError(
                "Staff project DB is unavailable", status_code=502
            ) from exc

        _token_project_ids_cache[normalized_token] = (
            now + max(int(cache_ttl_seconds), 1),
            ids,
        )
        return set(ids)

    @staticmethod
    async def list_visible_project_ids_for_username_from_db(
        db: AsyncSession,
        username: str,
    ) -> set[int]:
        """DB-only variant of the visibility lookup."""
        try:
            staff_user_id = await _resolve_staff_user_id(db, username)
            if staff_user_id is None:
                return set()
            return await _list_visible_project_ids_for_user_id(db, staff_user_id)
        except SQLAlchemyError:
            return set()

    # ----------------------------------------------------------- can-mng
    @staticmethod
    async def can_manage_project_for_username_from_db(
        db: AsyncSession,
        *,
        username: str,
        remote_project_id: int,
    ) -> bool:
        """SUPER_ADMIN, project-admin or owning-dept admin can manage."""
        try:
            project_id = int(remote_project_id)
        except Exception:
            return False
        if project_id <= 0:
            return False

        staff_user_id = await _resolve_staff_user_id(db, username)
        if staff_user_id is None:
            return False

        super_admin_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(StaffUserRole)
                    .join(StaffRole, StaffRole.id == StaffUserRole.role_id)
                    .where(
                        StaffUserRole.user_id == staff_user_id,
                        StaffRole.code == "SUPER_ADMIN",
                    )
                )
            ).scalar_one()
            or 0
        )
        if super_admin_count > 0:
            return True

        project_admin_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(StaffProjectUser)
                    .where(
                        StaffProjectUser.project_id == project_id,
                        StaffProjectUser.user_id == staff_user_id,
                        StaffProjectUser.type == 1,
                    )
                )
            ).scalar_one()
            or 0
        )
        if project_admin_count > 0:
            return True

        # Department admin of the project's owning department.
        dept_admin_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(StaffProject)
                    .join(
                        StaffDepartmentUser,
                        StaffDepartmentUser.department_id == StaffProject.department_id,
                    )
                    .where(
                        StaffProject.id == project_id,
                        StaffDepartmentUser.user_id == staff_user_id,
                        StaffDepartmentUser.type == 1,
                    )
                )
            ).scalar_one()
            or 0
        )
        return dept_admin_count > 0

    # ------------------------------------------------------------ snapshot
    @staticmethod
    async def get_permission_snapshot_for_username_from_db(
        db: AsyncSession,
        *,
        username: str,
    ) -> SecurityServerPermissionSnapshot:
        """Returns (is_super_admin, is_admin_anywhere) for a staff user."""
        try:
            staff_user_id = await _resolve_staff_user_id(db, username)
            if staff_user_id is None:
                return SecurityServerPermissionSnapshot(False, False)

            super_admin_count = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(StaffUserRole)
                        .join(StaffRole, StaffRole.id == StaffUserRole.role_id)
                        .where(
                            StaffUserRole.user_id == staff_user_id,
                            StaffRole.code == "SUPER_ADMIN",
                        )
                    )
                ).scalar_one()
                or 0
            )
            is_super = super_admin_count > 0

            if is_super:
                return SecurityServerPermissionSnapshot(True, True)

            dept_admin = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(StaffDepartmentUser)
                        .where(
                            StaffDepartmentUser.user_id == staff_user_id,
                            StaffDepartmentUser.type == 1,
                        )
                    )
                ).scalar_one()
                or 0
            )
            project_admin = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(StaffProjectUser)
                        .where(
                            StaffProjectUser.user_id == staff_user_id,
                            StaffProjectUser.type == 1,
                        )
                    )
                ).scalar_one()
                or 0
            )
            group_admin = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(StaffGroupUser)
                        .where(
                            StaffGroupUser.user_id == staff_user_id,
                            StaffGroupUser.type == 1,
                        )
                    )
                ).scalar_one()
                or 0
            )
            is_admin = (dept_admin + project_admin + group_admin) > 0
            return SecurityServerPermissionSnapshot(False, is_admin)
        except SQLAlchemyError:
            # The legacy code swallowed cross-schema lookup errors so that
            # login still succeeded; keep that defensive behaviour.
            return SecurityServerPermissionSnapshot(False, False)

    # ------------------------------------------------------------- raw
    @staticmethod
    async def list_visible_projects_raw(
        *,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Spring-style `Result<List<Project>>` envelope used by `/api/projects` proxy."""
        if not SecurityServerProjectService.is_enabled():
            raise SecurityServerProjectServiceError(
                "Security server project sync is not enabled", status_code=503
            )

        page_size = max(int(limit or 100), 1)
        page_num = max(int((skip or 0) // page_size) + 1, 1)

        try:
            async with AsyncSessionLocal() as session:
                base = select(StaffProject)
                if active is True:
                    base = base.where(StaffProject.status == 1)
                elif active is False:
                    base = base.where(StaffProject.status != 1)

                total = int(
                    (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0
                )

                stmt = base.order_by(StaffProject.id.asc()).offset((page_num - 1) * page_size).limit(page_size)
                rows = (await session.execute(stmt)).scalars().all()
        except SQLAlchemyError as exc:
            raise SecurityServerProjectServiceError(
                "Staff project DB is unavailable", status_code=502
            ) from exc

        return {
            "code": 200,
            "message": "操作成功",
            "data": [_project_to_dto(p) for p in rows],
            "page": {"pageNum": page_num, "pageSize": page_size, "total": total},
        }

    @staticmethod
    async def get_project_detail_raw(project_id: int) -> dict[str, Any]:
        """Mirrors Spring's `GET /api/projects/{id}` envelope."""
        if not SecurityServerProjectService.is_enabled():
            raise SecurityServerProjectServiceError(
                "Security server project sync is not enabled", status_code=503
            )
        try:
            pid = int(project_id)
        except Exception as exc:
            raise SecurityServerProjectServiceError(
                "Invalid project id", status_code=400
            ) from exc

        try:
            async with AsyncSessionLocal() as session:
                project = await session.get(StaffProject, pid)
        except SQLAlchemyError as exc:
            raise SecurityServerProjectServiceError(
                "Staff project DB is unavailable", status_code=502
            ) from exc

        if project is None:
            raise SecurityServerProjectServiceError("Project not found", status_code=404)

        return {
            "code": 200,
            "message": "操作成功",
            "data": _project_to_dto(project),
        }

    @staticmethod
    def _parse_datetime(raw_value: Any) -> Optional[datetime]:
        """Preserved for legacy callers that import this helper."""
        if raw_value is None:
            return None
        text = str(raw_value).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
