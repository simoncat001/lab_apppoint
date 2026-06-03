from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.api.project_context import CurrentProjectContext, get_current_project_context
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    days: int = Query(30, ge=1, le=365),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project_ctx: CurrentProjectContext = Depends(get_current_project_context),
):
    """预约报表仪表盘。"""

    service = DashboardService(db)
    return await service.get_dashboard_report(
        current_user=current_user,
        current_project_id=project_ctx.project_id,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )
