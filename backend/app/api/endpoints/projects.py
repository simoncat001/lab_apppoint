from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectExternalBookingAccessUpdate,
    ProjectJoinRequestCreate,
    ProjectJoinRequestResponse,
    ProjectJoinRequestReview,
    ProjectJoinRequestStatus,
    ProjectUpdate,
)
from app.services.project_service import ProjectJoinRequestError, ProjectService
from app.services.security_server_project_service import SecurityServerProjectService, SecurityServerProjectServiceError
from app.services.security_server_auth_service import SecurityServerAuthService

router = APIRouter()


def _projects_managed_by_security_server() -> bool:
    # The legacy Spring service is gone — staff endpoints are now in-process.
    # `SECURITY_SERVER_BASE_URL` has been removed from settings; the single
    # boolean is enough to know whether the staff/projects integration is on.
    return bool(settings.SECURITY_SERVER_ENABLED)


def _ensure_security_project_sync_ready() -> None:
    if SecurityServerProjectService.is_enabled():
        return
    raise HTTPException(
        status_code=503,
        detail=(
            "Projects are managed by the security service, but project sync is not configured. "
            "Please configure SECURITY_SERVER_PROJECT_SYNC_ENABLED=true and service credentials."
        ),
    )


def _reject_local_project_mutation() -> None:
    raise HTTPException(
        status_code=405,
        detail="Projects are managed by the security service and are read-only in this system",
    )


async def _ensure_project_admin(
    current_user: User,
    service: ProjectService,
    project_obj,
) -> None:
    if not await service.can_user_review_project_join_requests(current_user, project_obj):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project administrators can perform this action",
        )


async def _get_security_user_visible_project_ids(
    db: AsyncSession,
    current_user: User,
) -> set[int]:
    username = str(getattr(current_user, "username", "") or "").strip()
    if not username:
        return set()

    visible_ids: set[int] = set()

    if SecurityServerProjectService.is_enabled():
        token = SecurityServerAuthService.get_cached_user_token(username)
        if token:
            try:
                visible_ids = await SecurityServerProjectService.list_visible_project_ids_with_token(token)
            except SecurityServerProjectServiceError as exc:
                if exc.status_code == 401:
                    SecurityServerAuthService.clear_cached_user_token(username)
            if visible_ids:
                return visible_ids

    try:
        return await SecurityServerProjectService.list_visible_project_ids_for_username_from_db(
            db,
            username,
        )
    except Exception:
        return set()


async def _get_security_user_scoped_mirror_projects(
    *,
    db: AsyncSession,
    service: ProjectService,
    current_user: User,
    skip: int,
    limit: int,
    active: Optional[bool],
):
    remote_ids = await _get_security_user_visible_project_ids(db, current_user)
    if not remote_ids:
        return []

    allowed_identifiers = {
        ProjectService._security_project_identifier(remote_id)
        for remote_id in remote_ids
    }

    fetch_limit = max(skip + limit, 5000)
    local_projects = await service.get_projects(
        skip=0,
        limit=fetch_limit,
        active=active,
        account_id=None,
    )
    filtered = [
        project
        for project in local_projects
        if (getattr(project, "application_identifier", None) or "").strip() in allowed_identifiers
    ]
    return filtered[skip : skip + limit]


def _dedupe_projects_by_id(projects: list[Project]) -> list[Project]:
    deduped: list[Project] = []
    seen: set[int] = set()
    for project in projects:
        pid = int(getattr(project, "id", 0) or 0)
        if pid <= 0 or pid in seen:
            continue
        seen.add(pid)
        deduped.append(project)
    return deduped


@router.get("/")
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None,
    account_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目列表（统一认证开启时透传权鉴返回格式）"""
    if _projects_managed_by_security_server():
        if not (current_user.is_staff or current_user.is_superuser):
            raise HTTPException(status_code=403, detail="Only staff can access raw security project responses")
        _ensure_security_project_sync_ready()
        service = ProjectService(db)
        try:
            # Keep local mirror fresh for tool/account bindings while returning raw response to clients.
            await service.sync_projects_from_security_server()
            return await SecurityServerProjectService.list_visible_projects_raw(
                skip=skip,
                limit=limit,
                active=active,
            )
        except SecurityServerProjectServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return await _get_local_mirror_projects(
        skip=skip,
        limit=limit,
        active=active,
        account_id=account_id,
        db=db,
        current_user=current_user,
    )


@router.get("/mirror", response_model=List[Project])
async def get_projects_mirror(
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None,
    account_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取本地项目镜像列表（兼容本系统内部 project_id 关联）"""
    return await _get_local_mirror_projects(
        skip=skip,
        limit=limit,
        active=active,
        account_id=account_id,
        db=db,
        current_user=current_user,
    )


@router.get("/joinable", response_model=List[Project])
async def get_joinable_projects(
    db: AsyncSession = Depends(get_db),
):
    """获取可对外展示的项目列表（用于外部用户申请页展示，无权限过滤）"""
    service = ProjectService(db)
    if _projects_managed_by_security_server():
        # Best-effort sync: external "project access request" list should still work from
        # locally configured mirror metadata even if security-server project visibility is
        # temporarily unavailable or service account lacks permission.
        if SecurityServerProjectService.is_enabled():
            try:
                await service.sync_projects_from_security_server()
            except SecurityServerProjectServiceError:
                pass
    # Ensure externally visible projects are backed by local org accounts so submitted requests
    # can proceed without manual pre-binding.
    await service.ensure_org_accounts_for_public_external_projects()
    return await service.list_public_external_booking_projects()


@router.get("/join-requests/my", response_model=List[ProjectJoinRequestResponse])
async def get_my_project_join_requests(
    status_filter: ProjectJoinRequestStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的项目加入申请记录"""
    service = ProjectService(db)
    return await service.list_project_join_requests_for_user(
        current_user.id,
        status=status_filter,
        limit=limit,
    )


@router.post(
    "/join-requests",
    response_model=ProjectJoinRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_join_request(
    payload: ProjectJoinRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交项目加入申请（外部用户）"""
    service = ProjectService(db)
    try:
        return await service.create_project_join_request(
            requester_user=current_user,
            target_project_id=payload.target_project_id,
            reason=payload.reason,
        )
    except ProjectJoinRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.post("/join-requests/{request_id}/cancel", response_model=ProjectJoinRequestResponse)
async def cancel_project_join_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销本人待审批的项目加入申请"""
    service = ProjectService(db)
    try:
        request_obj = await service.cancel_project_join_request(
            request_id=request_id,
            requester_user=current_user,
        )
    except ProjectJoinRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project join request not found")
    return request_obj


@router.get("/join-requests/pending-for-approval", response_model=List[ProjectJoinRequestResponse])
async def get_project_join_requests_for_current_project_approval(
    status_filter: ProjectJoinRequestStatus | None = Query(ProjectJoinRequestStatus.PENDING, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """获取当前项目下待审批的项目加入申请（项目管理员）"""
    service = ProjectService(db)
    await _ensure_project_admin(current_user, service, project_ctx.project)
    return await service.list_project_join_requests_for_target_project(
        project_ctx.project_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/join-requests/{request_id}/approve", response_model=ProjectJoinRequestResponse)
async def approve_project_join_request(
    request_id: int,
    payload: ProjectJoinRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """审批通过项目加入申请（当前项目管理员）"""
    service = ProjectService(db)
    await _ensure_project_admin(current_user, service, project_ctx.project)
    try:
        request_obj = await service.approve_project_join_request(
            request_id=request_id,
            reviewer_user=current_user,
            project_id=project_ctx.project_id,
            comment=payload.comment,
        )
    except ProjectJoinRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project join request not found")
    return request_obj


@router.post("/join-requests/{request_id}/reject", response_model=ProjectJoinRequestResponse)
async def reject_project_join_request(
    request_id: int,
    payload: ProjectJoinRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """驳回项目加入申请（当前项目管理员）"""
    service = ProjectService(db)
    await _ensure_project_admin(current_user, service, project_ctx.project)
    try:
        request_obj = await service.reject_project_join_request(
            request_id=request_id,
            reviewer_user=current_user,
            project_id=project_ctx.project_id,
            comment=payload.comment,
        )
    except ProjectJoinRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project join request not found")
    return request_obj


async def _get_local_mirror_projects(
    *,
    skip: int,
    limit: int,
    active: Optional[bool],
    account_id: Optional[int],
    db: AsyncSession,
    current_user: User,
):
    service = ProjectService(db)
    if _projects_managed_by_security_server():
        if SecurityServerProjectService.is_enabled():
            try:
                await service.sync_projects_from_security_server()
            except SecurityServerProjectServiceError:
                pass

    # 本地项目权限（外部用户审批流）始终生效，不依赖权鉴可见性
    local_accessible_project_ids: list[int] = []
    if not (current_user.is_staff or current_user.is_superuser):
        local_accessible_project_ids = await service.list_accessible_project_ids_for_user(current_user.id)

    auth_source = (getattr(current_user, "auth_source", None) or "local").lower()
    if current_user.is_staff or current_user.is_superuser:
        return await service.get_projects(
            skip=skip, limit=limit, active=active, account_id=account_id
        )

    if auth_source == "security_server":
        fetch_limit = max(skip + limit, 5000)
        scoped_projects = await _get_security_user_scoped_mirror_projects(
            db=db,
            service=service,
            current_user=current_user,
            skip=0,
            limit=fetch_limit,
            active=active,
        )
        if account_id is not None:
            raise HTTPException(status_code=400, detail="account_id filter is not supported for non-staff users")

        local_projects: list[Project] = []
        if local_accessible_project_ids:
            local_projects = await service.get_projects(
                skip=0,
                limit=fetch_limit,
                active=active,
                project_ids=local_accessible_project_ids,
            )

        merged_projects = _dedupe_projects_by_id([*scoped_projects, *local_projects])
        return merged_projects[skip : skip + limit]

    # 普通本地用户：基于项目访问权限，不再使用结算账户绑定做过滤
    if not local_accessible_project_ids:
        return []

    if account_id is not None:
        raise HTTPException(status_code=400, detail="account_id filter is not supported for non-staff users")

    return await service.get_projects(
        skip=skip,
        limit=limit,
        active=active,
        project_ids=local_accessible_project_ids,
    )


@router.get("/mirror/{project_id}", response_model=Project)
async def get_project_mirror(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取本地项目镜像详情"""
    service = ProjectService(db)
    if _projects_managed_by_security_server():
        if SecurityServerProjectService.is_enabled():
            try:
                await service.sync_projects_from_security_server()
            except SecurityServerProjectServiceError:
                pass
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not (current_user.is_staff or current_user.is_superuser):
        auth_source = (getattr(current_user, "auth_source", None) or "local").lower()
        if auth_source == "security_server":
            visible_project_ids = await _get_security_user_visible_project_ids(db, current_user)
            identifier = (getattr(project, "application_identifier", None) or "").strip()
            if identifier.startswith("security-server:"):
                remote_part = identifier.split(":", 1)[1].strip()
                try:
                    remote_id = int(remote_part)
                except Exception:
                    remote_id = None
                if remote_id is not None and remote_id in visible_project_ids:
                    return project
            # 本地审批流兜底：外部项目权限由本地管理时，允许访问镜像项目
            if await service.user_has_project_access(current_user.id, project.id):
                return project
            raise HTTPException(status_code=403, detail="Not authorized to access this project")

        if not await service.user_has_project_access(current_user.id, project.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this project")
    return project


@router.patch("/mirror/{project_id}/external-booking-access", response_model=Project)
async def set_project_external_booking_access(
    project_id: int,
    payload: ProjectExternalBookingAccessUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员配置项目是否对外开放预约权限申请（本地镜像元数据）"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=403, detail="Only staff can configure project external booking access")

    service = ProjectService(db)
    if _projects_managed_by_security_server():
        if SecurityServerProjectService.is_enabled():
            try:
                # best effort sync before applying local metadata config
                await service.sync_projects_from_security_server()
            except SecurityServerProjectServiceError:
                pass

    project = await service.set_external_booking_request_open(
        project_id,
        allow_external_booking_request=payload.allow_external_booking_request,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """获取项目详情（统一认证开启时透传权鉴返回格式）"""
    if _projects_managed_by_security_server():
        if not (current_user.is_staff or current_user.is_superuser):
            raise HTTPException(status_code=403, detail="Only staff can access raw security project responses")
        _ensure_security_project_sync_ready()
        service = ProjectService(db)
        try:
            # Best effort mirror sync for downstream local relations.
            await service.sync_projects_from_security_server()
            return await SecurityServerProjectService.get_project_detail_raw(project_id)
        except SecurityServerProjectServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=Project)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建项目"""
    if _projects_managed_by_security_server():
        _reject_local_project_mutation()
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can create projects")
    service = ProjectService(db)
    try:
        return await service.create_project(project_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新项目"""
    if _projects_managed_by_security_server():
        _reject_local_project_mutation()
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can update projects")
    service = ProjectService(db)
    try:
        project = await service.update_project(project_id, project_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除项目"""
    if _projects_managed_by_security_server():
        _reject_local_project_mutation()
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can delete projects")
    service = ProjectService(db)
    success = await service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}
