from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    total_tools: int
    active_users: int
    report_users: int
    total_reservations: int
    total_hours: float
    active_tasks: int
    distinct_tools: int
    distinct_projects: int
    ongoing_reservations: int
    upcoming_reservations: int
    completed_reservations: int
    cancelled_reservations: int
    missed_reservations: int


class DashboardRecentReservation(BaseModel):
    user_name: Optional[str] = None
    tool_name: Optional[str] = None
    project_name: Optional[str] = None
    start: datetime
    end: datetime
    status: str


class DashboardPendingTask(BaseModel):
    creator_name: Optional[str] = None
    tool_name: Optional[str] = None
    problem_description: Optional[str] = None
    urgency: int
    creation_time: datetime


class DashboardStatusBreakdown(BaseModel):
    key: str
    label: str
    count: int


class DashboardTrendPoint(BaseModel):
    date: date
    total: int
    ongoing: int
    completed: int
    upcoming: int
    cancelled: int
    missed: int


class DashboardRankingItem(BaseModel):
    name: str
    reservation_count: int
    total_hours: float


class DashboardUserReport(BaseModel):
    user_id: int
    username: str
    full_name: str
    is_active: bool
    is_staff: bool
    is_verified: bool
    total_reservations: int
    ongoing_reservations: int
    completed_reservations: int
    upcoming_reservations: int
    cancelled_reservations: int
    missed_reservations: int
    total_hours: float
    distinct_tools: int
    distinct_projects: int
    favorite_tool_name: Optional[str] = None
    latest_reservation_at: Optional[datetime] = None
    next_reservation_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    scope: str
    period_start: date
    period_end: date
    stats: DashboardStats
    status_breakdown: List[DashboardStatusBreakdown]
    trend: List[DashboardTrendPoint]
    tool_rankings: List[DashboardRankingItem]
    project_rankings: List[DashboardRankingItem]
    user_reports: List[DashboardUserReport]
    current_user_report: DashboardUserReport
    recent_reservations: List[DashboardRecentReservation]
    pending_tasks: List[DashboardPendingTask]

    model_config = ConfigDict(from_attributes=True)
