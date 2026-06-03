from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, status, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.core.media import save_image_upload
from app.db.session import get_db
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.services.announcement_service import AnnouncementService

router = APIRouter()


@router.get("/", response_model=List[AnnouncementResponse])
async def list_announcements(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_unpublished: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = AnnouncementService(db)
    if not current_user.is_staff:
        include_unpublished = False
    items = await service.get_announcements(
        project_id=project_ctx.project_id,
        skip=skip,
        limit=limit,
        include_unpublished=include_unpublished,
    )
    total = await service.count_announcements(
        project_id=project_ctx.project_id,
        include_unpublished=include_unpublished,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement_detail(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = AnnouncementService(db)
    announcement = await service.get_announcement(announcement_id, project_ctx.project_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if (not current_user.is_staff) and (not announcement.published):
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    payload: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can create announcements")
    service = AnnouncementService(db)
    return await service.create_announcement(payload, current_user.id, project_ctx.project_id)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can update announcements")
    service = AnnouncementService(db)
    announcement = await service.update_announcement(announcement_id, payload, project_ctx.project_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


@router.post("/{announcement_id}/image")
async def upload_announcement_image(
    announcement_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """
    上传公告内嵌图片（仅员工）

    图片落在 media/announcements/{announcement_id}/ 下，公告删除时整个目录级联清理。
    返回 WangEditor 要求的格式 {errno: 0, data: {url, alt, href}}。
    """
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can upload images")

    service = AnnouncementService(db)
    announcement = await service.get_announcement(announcement_id, project_ctx.project_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    filename, url = await save_image_upload("announcements", announcement_id, file)
    return {"errno": 0, "data": {"url": url, "alt": filename, "href": url}}


@router.delete("/{announcement_id}", response_model=bool)
async def delete_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can delete announcements")
    service = AnnouncementService(db)
    success = await service.delete_announcement(announcement_id, project_ctx.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return True
