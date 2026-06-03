"""Staff project DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.staff.common import BasePageRequest, StaffSchema


class ProjectQuery(BasePageRequest):
    department_id: Optional[int] = Field(default=None, alias="departmentId")


class ProjectRequest(StaffSchema):
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = Field(default=None, alias="departmentId")
    external_visible: Optional[bool] = Field(default=None, alias="externalVisible")
    external_display_name: Optional[str] = Field(default=None, alias="externalDisplayName")


class ProjectItem(StaffSchema):
    id: int
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = Field(default=None, alias="departmentId")
    leader_id: Optional[int] = Field(default=None, alias="leaderId")
    status: Optional[int] = None
    external_visible: Optional[bool] = Field(default=None, alias="externalVisible")
    external_display_name: Optional[str] = Field(default=None, alias="externalDisplayName")
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    updated_time: Optional[datetime] = Field(default=None, alias="updatedTime")
    joined: bool = False
    can_manage: bool = Field(default=False, alias="canManage")
    can_set_admin: bool = Field(default=False, alias="canSetAdmin")


class ProjectDetail(StaffSchema):
    id: int
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = Field(default=None, alias="departmentId")
    leader_id: Optional[int] = Field(default=None, alias="leaderId")
    status: Optional[int] = None
    external_visible: bool = Field(default=False, alias="externalVisible")
    external_display_name: Optional[str] = Field(default=None, alias="externalDisplayName")
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    member_count: int = Field(default=0, alias="memberCount")
    group_count: int = Field(default=0, alias="groupCount")
