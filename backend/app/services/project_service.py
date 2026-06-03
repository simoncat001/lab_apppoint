import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account, account_members
from app.models.project import Project, ProjectJoinRequest
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectJoinRequestStatus,
    ProjectUpdate,
)
from app.services.account_service import AccountService
from app.services.security_server_project_service import (
    SecurityServerProjectRecord,
    SecurityServerProjectService,
)

logger = logging.getLogger(__name__)


class ProjectJoinRequestError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _build_unique_auto_project_account_name(self, project: Project) -> str:
        """Build a unique local org account name for a project."""
        preferred = (getattr(project, "external_display_name", None) or project.name or "").strip()
        base_name_raw = f"项目账户-{preferred or project.id}"
        base_name = base_name_raw[:100].strip() or f"项目账户-{project.id}"
        candidate = base_name
        suffix = 0
        while True:
            exists = await self.db.scalar(select(Account.id).where(Account.name == candidate))
            if exists is None:
                return candidate
            suffix += 1
            suffix_text = f"-P{project.id}" if suffix == 1 else f"-P{project.id}-{suffix}"
            trimmed = base_name[: max(1, 100 - len(suffix_text))]
            candidate = f"{trimmed}{suffix_text}"

    async def _get_bound_account_for_project(self, project: Project) -> Optional[Account]:
        if project.account_id is None:
            return None
        result = await self.db.execute(
            select(Account)
            .options(selectinload(Account.type), selectinload(Account.members))
            .where(Account.id == project.account_id)
        )
        return result.scalar_one_or_none()

    async def ensure_org_accounts_for_public_external_projects(self) -> int:
        """Ensure every externally visible project has a local manual-membership org account."""
        result = await self.db.execute(
            select(Project).where(
                Project.active.is_(True),
                Project.allow_external_booking_request.is_(True),
            )
        )
        projects = list(result.scalars().all())
        if not projects:
            return 0

        created_or_fixed = 0
        for project in projects:
            bound_account = await self._get_bound_account_for_project(project)
            if bound_account is not None and AccountService._is_manual_membership_org_account(bound_account):
                continue

            account_name = await self._build_unique_auto_project_account_name(project)
            account = Account(
                name=account_name,
                user_id=None,
                active=True,
                note=f"Auto-created from external project list sync (project_id={project.id})",
            )
            self.db.add(account)
            await self.db.flush()
            await AccountService._bind_account_to_project(self.db, account.id, project.id)
            project.account_id = account.id
            created_or_fixed += 1

        if created_or_fixed:
            await self.db.commit()
        return created_or_fixed

    async def ensure_org_account_for_project(self, project_id: int) -> Optional[Project]:
        """Ensure a single project has a local organization account bound.

        Used by reservation flow as a safety net so project-level accounting can proceed
        even when historical data missed account binding.
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        bound_account = await self._get_bound_account_for_project(project)
        if bound_account is not None:
            if project.account_id != bound_account.id:
                project.account_id = bound_account.id
                await self.db.commit()
                await self.db.refresh(project)
            return project

        account_name = await self._build_unique_auto_project_account_name(project)
        account = Account(
            name=account_name,
            user_id=None,
            active=True,
            note=f"Auto-created for reservation fallback (project_id={project.id})",
        )
        self.db.add(account)
        await self.db.flush()
        await AccountService._bind_account_to_project(self.db, account.id, project.id)
        project.account_id = account.id
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def _ensure_project_manual_org_account(self, project: Project) -> Account:
        """Validate project has a local manual-membership organization account bound."""
        if project.account_id is None:
            raise ProjectJoinRequestError(
                "Target project is not yet bound to a local organization account"
            )
        result = await self.db.execute(
            select(Account)
            .options(selectinload(Account.type), selectinload(Account.members))
            .where(Account.id == project.account_id)
        )
        existing_account = result.scalar_one_or_none()
        if not existing_account:
            raise ProjectJoinRequestError("Target project's bound account no longer exists")
        if not AccountService._is_manual_membership_org_account(existing_account):
            raise ProjectJoinRequestError("Target project does not support manual join requests")
        return existing_account

    async def sync_projects_from_security_server(self) -> int:
        """Sync visible projects from security-server into local read-only mirror.

        Local project rows are identified by `application_identifier = security-server:{remote_id}`.
        We keep `account_id` untouched because it is local billing/organization binding.
        """
        if not SecurityServerProjectService.is_enabled():
            return 0

        records = await SecurityServerProjectService.list_visible_projects()
        if not records:
            return 0

        result = await self.db.execute(select(Project))
        existing_projects = list(result.scalars().all())

        by_identifier = {
            (project.application_identifier or "").strip(): project
            for project in existing_projects
            if project.application_identifier
        }
        by_name = {project.name: project for project in existing_projects}

        touched_identifiers: set[str] = set()
        updated_count = 0

        for record in records:
            identifier = self._security_project_identifier(record.remote_id)
            touched_identifiers.add(identifier)
            project = by_identifier.get(identifier)
            target_name = self._pick_unique_project_name(record, existing_projects, current=project)

            if project:
                changed = False
                if project.name != target_name:
                    project.name = target_name
                    changed = True
                if project.active != record.active:
                    project.active = record.active
                    changed = True
                if record.external_visible is not None:
                    external_open = bool(record.external_visible)
                    if project.allow_external_booking_request != external_open:
                        project.allow_external_booking_request = external_open
                        changed = True
                if project.external_display_name != record.external_display_name:
                    project.external_display_name = record.external_display_name
                    changed = True
                if record.created_at and project.start_date != record.created_at:
                    project.start_date = record.created_at
                    changed = True
                if changed:
                    updated_count += 1
                continue

            project = Project(
                name=target_name,
                application_identifier=identifier,
                active=record.active,
                start_date=record.created_at,
                allow_external_booking_request=bool(record.external_visible),
                external_display_name=record.external_display_name,
            )
            self.db.add(project)
            existing_projects.append(project)
            by_identifier[identifier] = project
            by_name[target_name] = project
            updated_count += 1

        # Soft-disable projects that were previously synced but no longer visible in security-server.
        for project in existing_projects:
            app_id = (project.application_identifier or "").strip()
            if not app_id.startswith("security-server:"):
                continue
            if app_id not in touched_identifiers and project.active:
                project.active = False
                updated_count += 1

        if updated_count:
            await self.db.commit()
        return updated_count

    @staticmethod
    def _security_project_identifier(remote_id: int) -> str:
        return f"security-server:{int(remote_id)}"

    @staticmethod
    def _pick_unique_project_name(
        record: SecurityServerProjectRecord,
        all_projects: List[Project],
        *,
        current: Optional[Project] = None,
    ) -> str:
        base_name = record.name[:200]
        candidate = base_name
        suffix = 0
        while True:
            conflict = None
            for project in all_projects:
                if current is not None and project is current:
                    continue
                if project.name == candidate:
                    conflict = project
                    break
            if conflict is None:
                return candidate
            suffix += 1
            suffix_text = f" [{record.remote_id}]" if suffix == 1 else f" [{record.remote_id}-{suffix}]"
            trimmed = base_name[: max(1, 200 - len(suffix_text))]
            candidate = f"{trimmed}{suffix_text}"

    async def get_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
        account_id: Optional[int] = None,
        account_ids: Optional[List[int]] = None,
        project_ids: Optional[List[int]] = None,
    ) -> List[Project]:
        query = select(Project)
        if active is not None:
            query = query.where(Project.active == active)
        if project_ids is not None:
            if not project_ids:
                return []
            query = query.where(Project.id.in_(project_ids))
        if account_ids is not None:
            query = query.where(Project.account_id.in_(account_ids))
        elif account_id is not None:
            query = query.where(Project.account_id == account_id)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_project(self, project_id: int) -> Optional[Project]:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def _ensure_account_binding_available(
        self,
        account_id: Optional[int],
        *,
        exclude_project_id: Optional[int] = None,
    ) -> None:
        if account_id is None:
            return
        query = select(Project).where(Project.account_id == account_id)
        if exclude_project_id is not None:
            query = query.where(Project.id != exclude_project_id)
        existing = await self.db.scalar(query)
        if existing:
            raise ValueError(
                f"Account {account_id} is already bound to project '{existing.name}'"
            )

    async def create_project(self, project_in: ProjectCreate) -> Project:
        await self._ensure_account_binding_available(project_in.account_id)
        project = Project(**project_in.model_dump())
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(
        self, project_id: int, project_in: ProjectUpdate
    ) -> Optional[Project]:
        project = await self.get_project(project_id)
        if not project:
            return None

        update_data = project_in.model_dump(exclude_unset=True)
        if "account_id" in update_data:
            await self._ensure_account_binding_available(
                update_data["account_id"], exclude_project_id=project_id
            )
        
        for field, value in update_data.items():
            setattr(project, field, value)
            
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def set_external_booking_request_open(
        self,
        project_id: int,
        *,
        allow_external_booking_request: bool,
    ) -> Optional[Project]:
        project = await self.get_project(project_id)
        if not project:
            return None
        project.allow_external_booking_request = bool(allow_external_booking_request)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int) -> bool:
        project = await self.get_project(project_id)
        if not project:
            return False
            
        await self.db.delete(project)
        await self.db.commit()
        return True

    # ==================== Project Join Request Workflow ====================
    def _project_join_request_query(self):
        return (
            select(ProjectJoinRequest)
            .options(
                selectinload(ProjectJoinRequest.requester),
                selectinload(ProjectJoinRequest.reviewer),
                selectinload(ProjectJoinRequest.source_project),
                selectinload(ProjectJoinRequest.target_project),
            )
        )

    async def _get_project_join_request(self, request_id: int) -> Optional[ProjectJoinRequest]:
        result = await self.db.execute(
            self._project_join_request_query().where(ProjectJoinRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def _get_project_with_account(self, project_id: int) -> Optional[Project]:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.account).selectinload(Account.type))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def user_has_project_access(self, user_id: int, project_id: int) -> bool:
        """Project access check decoupled from project receiving account.

        Access sources:
        1) approved project join request records (new behavior)
        2) legacy account-membership binding (backward compatibility)
        """
        approved = await self.db.scalar(
            select(ProjectJoinRequest.id).where(
                ProjectJoinRequest.requester_user_id == user_id,
                ProjectJoinRequest.target_project_id == project_id,
                ProjectJoinRequest.status == ProjectJoinRequestStatus.APPROVED.value,
            )
        )
        if approved is not None:
            return True

        legacy = await self.db.scalar(
            select(Project.id)
            .join(account_members, account_members.c.account_id == Project.account_id)
            .where(
                Project.id == project_id,
                account_members.c.user_id == user_id,
            )
        )
        return legacy is not None

    async def list_accessible_project_ids_for_user(self, user_id: int) -> List[int]:
        approved_rows = await self.db.execute(
            select(ProjectJoinRequest.target_project_id).where(
                ProjectJoinRequest.requester_user_id == user_id,
                ProjectJoinRequest.status == ProjectJoinRequestStatus.APPROVED.value,
            )
        )
        approved_ids = {int(project_id) for project_id in approved_rows.scalars().all()}

        legacy_rows = await self.db.execute(
            select(Project.id)
            .join(account_members, account_members.c.account_id == Project.account_id)
            .where(account_members.c.user_id == user_id)
        )
        legacy_ids = {int(project_id) for project_id in legacy_rows.scalars().all()}

        all_ids = approved_ids | legacy_ids
        return sorted(all_ids)

    async def list_joinable_projects_for_user(self, user: User) -> List[Project]:
        result = await self.db.execute(
            select(Project)
            .where(
                Project.active.is_(True),
                Project.allow_external_booking_request.is_(True),
            )
            .order_by(Project.name)
        )
        projects = list(result.scalars().all())
        accessible_project_ids = set(await self.list_accessible_project_ids_for_user(user.id))

        joinable: list[Project] = []
        for project in projects:
            if int(project.id) in accessible_project_ids:
                continue
            joinable.append(project)
        joinable.sort(
            key=lambda p: (
                ((getattr(p, "external_display_name", None) or p.name or "")).lower(),
                (p.name or "").lower(),
            )
        )
        return joinable

    async def list_public_external_booking_projects(self) -> List[Project]:
        """List projects configured for external display/booking request (no user-scoped filtering)."""
        result = await self.db.execute(
            select(Project)
            .where(
                Project.active.is_(True),
                Project.allow_external_booking_request.is_(True),
            )
        )
        projects = list(result.scalars().all())
        projects.sort(
            key=lambda p: (
                ((getattr(p, "external_display_name", None) or p.name or "")).lower(),
                (p.name or "").lower(),
            )
        )
        return projects

    async def list_project_join_requests_for_user(
        self,
        user_id: int,
        *,
        status: Optional[ProjectJoinRequestStatus] = None,
        limit: int = 20,
    ) -> List[ProjectJoinRequest]:
        query = self._project_join_request_query().where(ProjectJoinRequest.requester_user_id == user_id)
        if status is not None:
            query = query.where(ProjectJoinRequest.status == status.value)
        query = query.order_by(ProjectJoinRequest.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_project_join_requests_for_target_project(
        self,
        project_id: int,
        *,
        status: Optional[ProjectJoinRequestStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ProjectJoinRequest]:
        query = self._project_join_request_query().where(ProjectJoinRequest.target_project_id == project_id)
        if status is not None:
            query = query.where(ProjectJoinRequest.status == status.value)
        query = query.order_by(ProjectJoinRequest.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def can_user_review_project_join_requests(
        self,
        reviewer_user: User,
        target_project: Project,
    ) -> bool:
        if reviewer_user.is_staff or reviewer_user.is_superuser:
            return True

        username = str(getattr(reviewer_user, "username", "") or "").strip()
        if not username:
            return False

        identifier = (getattr(target_project, "application_identifier", None) or "").strip()
        if not identifier.startswith("security-server:"):
            return False

        remote_part = identifier.split(":", 1)[1].strip()
        try:
            remote_project_id = int(remote_part)
        except Exception:
            return False

        try:
            return await SecurityServerProjectService.can_manage_project_for_username_from_db(
                self.db,
                username=username,
                remote_project_id=remote_project_id,
            )
        except Exception:
            return False

    async def create_project_join_request(
        self,
        *,
        requester_user: User,
        target_project_id: int,
        reason: Optional[str] = None,
    ) -> ProjectJoinRequest:
        auth_source = (getattr(requester_user, "auth_source", None) or "local").lower()
        if auth_source != "local" or requester_user.is_staff or requester_user.is_superuser:
            raise ProjectJoinRequestError("Only external users can submit project join requests")

        duplicate_pending = await self.db.scalar(
            select(ProjectJoinRequest).where(
                ProjectJoinRequest.requester_user_id == requester_user.id,
                ProjectJoinRequest.target_project_id == target_project_id,
                ProjectJoinRequest.status == ProjectJoinRequestStatus.PENDING.value,
            )
        )
        if duplicate_pending:
            raise ProjectJoinRequestError("You already have a pending request for this project")

        target_project = await self._get_project_with_account(target_project_id)
        if not target_project:
            raise ProjectJoinRequestError("Target project not found")
        if not target_project.active:
            raise ProjectJoinRequestError("Target project is inactive")
        if not bool(getattr(target_project, "allow_external_booking_request", False)):
            raise ProjectJoinRequestError("Target project is not open for external booking requests")

        current_shared_account = await AccountService._get_current_shared_account_for_user(
            self.db, requester_user.id
        )
        source_project = None
        if await self.user_has_project_access(requester_user.id, target_project.id):
            raise ProjectJoinRequestError("You are already a member of the target project")
        if current_shared_account:
            source_project = await AccountService._get_project_bound_to_account(
                self.db, current_shared_account.id
            )

        join_request = ProjectJoinRequest(
            requester_user_id=requester_user.id,
            source_project_id=source_project.id if source_project else None,
            target_project_id=target_project.id,
            status=ProjectJoinRequestStatus.PENDING.value,
            reason=(reason or "").strip() or None,
        )
        self.db.add(join_request)
        await self.db.commit()
        loaded = await self._get_project_join_request(join_request.id)
        return loaded or join_request

    async def cancel_project_join_request(
        self,
        *,
        request_id: int,
        requester_user: User,
    ) -> Optional[ProjectJoinRequest]:
        join_request = await self._get_project_join_request(request_id)
        if not join_request:
            return None
        if join_request.requester_user_id != requester_user.id:
            raise ProjectJoinRequestError("You can only cancel your own requests")
        if join_request.status != ProjectJoinRequestStatus.PENDING.value:
            raise ProjectJoinRequestError("Only pending requests can be cancelled")

        join_request.status = ProjectJoinRequestStatus.CANCELLED.value
        join_request.reviewer_user_id = None
        join_request.review_comment = None
        join_request.reviewed_at = None
        join_request.updated_at = datetime.utcnow()
        await self.db.commit()
        loaded = await self._get_project_join_request(request_id)
        return loaded or join_request

    async def approve_project_join_request(
        self,
        *,
        request_id: int,
        reviewer_user: User,
        project_id: int,
        comment: Optional[str] = None,
    ) -> Optional[ProjectJoinRequest]:
        join_request = await self._get_project_join_request(request_id)
        if not join_request:
            return None
        if join_request.status != ProjectJoinRequestStatus.PENDING.value:
            raise ProjectJoinRequestError("Only pending requests can be approved")
        if int(join_request.target_project_id) != int(project_id):
            raise ProjectJoinRequestError("This request does not belong to the current project")

        target_project = await self._get_project_with_account(join_request.target_project_id)
        if not target_project:
            raise ProjectJoinRequestError("Target project not found")
        if not await self.can_user_review_project_join_requests(reviewer_user, target_project):
            raise ProjectJoinRequestError("Only project administrators can approve requests")
        if not target_project.active:
            raise ProjectJoinRequestError("Target project is inactive")
        if not bool(getattr(target_project, "allow_external_booking_request", False)):
            raise ProjectJoinRequestError("Target project is not open for external booking requests")

        join_request.status = ProjectJoinRequestStatus.APPROVED.value
        join_request.reviewer_user_id = reviewer_user.id
        join_request.review_comment = (comment or "").strip() or None
        join_request.reviewed_at = datetime.utcnow()
        join_request.updated_at = datetime.utcnow()
        await self.db.commit()
        loaded = await self._get_project_join_request(request_id)
        return loaded or join_request

    async def reject_project_join_request(
        self,
        *,
        request_id: int,
        reviewer_user: User,
        project_id: int,
        comment: Optional[str] = None,
    ) -> Optional[ProjectJoinRequest]:
        join_request = await self._get_project_join_request(request_id)
        if not join_request:
            return None
        if join_request.status != ProjectJoinRequestStatus.PENDING.value:
            raise ProjectJoinRequestError("Only pending requests can be rejected")
        if int(join_request.target_project_id) != int(project_id):
            raise ProjectJoinRequestError("This request does not belong to the current project")

        target_project = await self._get_project_with_account(join_request.target_project_id)
        if not target_project:
            raise ProjectJoinRequestError("Target project not found")
        if not await self.can_user_review_project_join_requests(reviewer_user, target_project):
            raise ProjectJoinRequestError("Only project administrators can reject requests")

        join_request.status = ProjectJoinRequestStatus.REJECTED.value
        join_request.reviewer_user_id = reviewer_user.id
        join_request.review_comment = (comment or "").strip() or None
        join_request.reviewed_at = datetime.utcnow()
        join_request.updated_at = datetime.utcnow()
        await self.db.commit()
        loaded = await self._get_project_join_request(request_id)
        return loaded or join_request
