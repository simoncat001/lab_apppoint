from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import (
    CurrentProjectContext,
    ensure_project_id_matches_current_project,
    get_current_project_context,
    get_tool_in_current_project,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.maintenance import MaintenanceRecordCreate, MaintenanceRecordUpdate, MaintenanceRecordResponse
from app.services.maintenance_service import MaintenanceService

router = APIRouter()


async def _get_record_in_current_project(
    service: MaintenanceService,
    record_id: int,
    project_ctx: CurrentProjectContext,
):
    record = await service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    ensure_project_id_matches_current_project(
        getattr(getattr(record, "tool", None), "project_id", None),
        project_ctx,
        detail_prefix="Maintenance record",
    )
    return record


@router.get("/", response_model=List[MaintenanceRecordResponse])
async def list_records(
    tool_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    service = MaintenanceService(db)
    if tool_id is not None:
        await get_tool_in_current_project(db, tool_id, project_ctx)
    return await service.list_records(tool_id=tool_id, project_id=project_ctx.project_id)


@router.post("/", response_model=MaintenanceRecordResponse)
async def create_record(
    payload: MaintenanceRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can create maintenance records")
    await get_tool_in_current_project(db, payload.tool_id, project_ctx)
    service = MaintenanceService(db)
    return await service.create_record(payload, current_user.id)


@router.put("/{record_id}", response_model=MaintenanceRecordResponse)
async def update_record(
    record_id: int,
    payload: MaintenanceRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can update maintenance records")
    service = MaintenanceService(db)
    await _get_record_in_current_project(service, record_id, project_ctx)
    record = await service.update_record(record_id, payload)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/{record_id}", response_model=bool)
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can delete maintenance records")
    service = MaintenanceService(db)
    await _get_record_in_current_project(service, record_id, project_ctx)
    success = await service.delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return True
