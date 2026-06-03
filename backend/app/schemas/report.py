from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectTopToolReport(BaseModel):
    tool_id: int
    tool_name: str
    reservation_count: int


class ProjectReportItem(BaseModel):
    project_id: int
    project_name: str
    external_display_name: Optional[str] = None
    active: bool
    tool_count: int
    active_tool_count: int = 0
    idle_tool_count: int = 0
    reservation_count: int
    cancelled_reservation_count: int
    paid_usage_count: int
    top_tools: List[ProjectTopToolReport] = Field(default_factory=list)


class GlobalTopToolReport(BaseModel):
    tool_id: int
    tool_name: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    reservation_count: int


class ProjectReportSummary(BaseModel):
    total_projects: int
    active_projects: int
    inactive_projects: int
    uncategorized_tools: int
    project_reports: List[ProjectReportItem] = Field(default_factory=list)
    top_tools: List[GlobalTopToolReport] = Field(default_factory=list)
