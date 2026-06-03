"""Research collaboration record endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import (
    CurrentProjectContext,
    get_current_project_context,
    get_reservation_in_current_project,
    get_tool_in_current_project,
)
from app.core.audit import diff_payload, record_audit
from app.core.config import settings
from app.core.media import save_file_upload, save_image_upload
from app.db.session import get_db
from app.models.collaboration import CollaborationRecord
from app.models.user import User
from app.schemas.collaboration import (
    CollaborationRecordCreate,
    CollaborationRecordResponse,
    CollaborationRecordType,
    CollaborationRecordUpdate,
    CollaborationStatus,
    CollaborationVisibility,
)
from app.services.collaboration_service import (
    CollaborationPermissionError,
    CollaborationService,
    CollaborationStateError,
)
from app.services.tool_service import ToolService

router = APIRouter()


def _permission_error(exc: CollaborationPermissionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


def _state_error(exc: CollaborationStateError | ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _snapshot(record: CollaborationRecord) -> dict:
    return {
        "title": record.title,
        "content": record.content,
        "content_format": record.content_format,
        "visibility": record.visibility,
        "status": record.status,
        "pinned": record.pinned,
    }


async def _ensure_tool_access(
    db: AsyncSession,
    *,
    tool_id: int,
    current_user: User,
    project_ctx: CurrentProjectContext,
) -> None:
    await get_tool_in_current_project(db, tool_id, project_ctx)
    if not await ToolService(db).check_external_user_tool_access(tool_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this tool")


async def _resolve_bound_tool_id(
    db: AsyncSession,
    *,
    payload_tool_id: Optional[int],
    reservation_id: Optional[int],
    current_user: User,
    project_ctx: CurrentProjectContext,
) -> Optional[int]:
    tool_id = payload_tool_id
    if reservation_id is not None:
        reservation = await get_reservation_in_current_project(db, reservation_id, project_ctx)
        if reservation.tool_id is not None:
            if tool_id is not None and int(tool_id) != int(reservation.tool_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tool_id does not match the reservation's tool_id",
                )
            tool_id = reservation.tool_id

    if tool_id is not None:
        await _ensure_tool_access(db, tool_id=tool_id, current_user=current_user, project_ctx=project_ctx)
    return tool_id


async def _get_record_or_404(
    service: CollaborationService,
    *,
    record_id: int,
    project_id: int,
) -> CollaborationRecord:
    record = await service.get_record(record_id, project_id=project_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaboration record not found")
    return record


@router.post("/", response_model=CollaborationRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_collaboration_record(
    payload: CollaborationRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    tool_id = await _resolve_bound_tool_id(
        db,
        payload_tool_id=payload.tool_id,
        reservation_id=payload.reservation_id,
        current_user=current_user,
        project_ctx=project_ctx,
    )
    service = CollaborationService(db)
    try:
        record = await service.create_record(
            payload,
            project_id=project_ctx.project_id,
            author_id=current_user.id,
            current_user=current_user,
            tool_id=tool_id,
        )
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc
    except CollaborationStateError as exc:
        raise _state_error(exc) from exc

    await record_audit(
        db,
        user_id=current_user.id,
        action="COLLABORATION_RECORD_CREATE",
        detail={"record_id": record.id, "project_id": record.project_id, "record_type": record.record_type},
    )
    return record


@router.get("/", response_model=List[CollaborationRecordResponse])
async def list_collaboration_records(
    response: Response,
    tool_id: Optional[int] = Query(None),
    reservation_id: Optional[int] = Query(None),
    record_type: Optional[CollaborationRecordType] = Query(None),
    status_filter: Optional[CollaborationStatus] = Query(None, alias="status"),
    visibility: Optional[CollaborationVisibility] = Query(None),
    keyword: Optional[str] = Query(None, max_length=200),
    mine: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if tool_id is not None:
        await _ensure_tool_access(db, tool_id=tool_id, current_user=current_user, project_ctx=project_ctx)
    if reservation_id is not None:
        await get_reservation_in_current_project(db, reservation_id, project_ctx)

    service = CollaborationService(db)
    items = await service.list_records(
        project_id=project_ctx.project_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        tool_id=tool_id,
        reservation_id=reservation_id,
        record_type=record_type,
        status=status_filter,
        visibility=visibility,
        keyword=keyword,
        author_id=current_user.id if mine else None,
    )
    total = await service.count_records(
        project_id=project_ctx.project_id,
        current_user=current_user,
        tool_id=tool_id,
        reservation_id=reservation_id,
        record_type=record_type,
        status=status_filter,
        visibility=visibility,
        keyword=keyword,
        author_id=current_user.id if mine else None,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.post("/media/image")
async def upload_collaboration_image(
    file: UploadFile = File(...),
    tool_id: Optional[int] = Query(None),
    reservation_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    上传科研协作记录富文本内嵌图片。

    新增记录保存前没有 record_id，因此先按当前项目存放：
    media/collaboration/{project_id}/{uuid}.{ext}
    返回 WangEditor 要求的 {errno, data} 结构。
    """
    await _resolve_bound_tool_id(
        db,
        payload_tool_id=tool_id,
        reservation_id=reservation_id,
        current_user=current_user,
        project_ctx=project_ctx,
    )
    filename, url = await save_image_upload("collaboration", project_ctx.project_id, file)
    return {"errno": 0, "data": {"url": url, "alt": filename, "href": url}}


@router.post("/media/video")
async def upload_collaboration_video(
    file: UploadFile = File(...),
    tool_id: Optional[int] = Query(None),
    reservation_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    上传科研协作记录富文本内嵌视频。

    视频同样按当前项目存放到 media/collaboration/{project_id}/。
    返回 WangEditor 要求的 {errno, data} 结构。
    """
    await _resolve_bound_tool_id(
        db,
        payload_tool_id=tool_id,
        reservation_id=reservation_id,
        current_user=current_user,
        project_ctx=project_ctx,
    )
    filename, url = await save_file_upload(
        "collaboration",
        project_ctx.project_id,
        file,
        max_size_mb=settings.COLLABORATION_VIDEO_MAX_SIZE_MB,
        allowed_content_types=settings.COLLABORATION_VIDEO_ALLOWED_TYPES,
    )
    return {"errno": 0, "data": {"url": url, "poster": "", "name": filename}}


@router.get("/{record_id}", response_model=CollaborationRecordResponse)
async def get_collaboration_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = CollaborationService(db)
    record = await _get_record_or_404(service, record_id=record_id, project_id=project_ctx.project_id)
    try:
        service.ensure_can_read(current_user, record)
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc
    return record


@router.put("/{record_id}", response_model=CollaborationRecordResponse)
async def update_collaboration_record(
    record_id: int,
    payload: CollaborationRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = CollaborationService(db)
    record = await _get_record_or_404(service, record_id=record_id, project_id=project_ctx.project_id)
    before = _snapshot(record)
    try:
        record = await service.update_record(record, payload, current_user=current_user)
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc
    except (CollaborationStateError, ValueError) as exc:
        raise _state_error(exc) from exc

    await record_audit(
        db,
        user_id=current_user.id,
        action="COLLABORATION_RECORD_UPDATE",
        detail={"record_id": record.id, "changes": diff_payload(before, _snapshot(record))},
    )
    return record


@router.delete("/{record_id}", response_model=bool)
async def delete_collaboration_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = CollaborationService(db)
    record = await _get_record_or_404(service, record_id=record_id, project_id=project_ctx.project_id)
    try:
        record = await service.soft_delete_record(record, current_user=current_user)
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc

    await record_audit(
        db,
        user_id=current_user.id,
        action="COLLABORATION_RECORD_DELETE",
        detail={"record_id": record.id, "project_id": record.project_id},
    )
    return True


@router.post("/{record_id}/publish", response_model=CollaborationRecordResponse)
async def publish_collaboration_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = CollaborationService(db)
    record = await _get_record_or_404(service, record_id=record_id, project_id=project_ctx.project_id)
    try:
        record = await service.publish_record(record, current_user=current_user)
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc
    except CollaborationStateError as exc:
        raise _state_error(exc) from exc

    await record_audit(
        db,
        user_id=current_user.id,
        action="COLLABORATION_RECORD_PUBLISH",
        detail={"record_id": record.id, "project_id": record.project_id},
    )
    return record


@router.post("/{record_id}/archive", response_model=CollaborationRecordResponse)
async def archive_collaboration_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = CollaborationService(db)
    record = await _get_record_or_404(service, record_id=record_id, project_id=project_ctx.project_id)
    try:
        record = await service.archive_record(record, current_user=current_user)
    except CollaborationPermissionError as exc:
        raise _permission_error(exc) from exc
    except CollaborationStateError as exc:
        raise _state_error(exc) from exc

    await record_audit(
        db,
        user_id=current_user.id,
        action="COLLABORATION_RECORD_ARCHIVE",
        detail={"record_id": record.id, "project_id": record.project_id},
    )
    return record
