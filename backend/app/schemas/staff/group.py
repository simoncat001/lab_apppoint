"""Staff group DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.staff.common import BasePageRequest, StaffSchema


class GroupQuery(BasePageRequest):
    project_id: Optional[int] = Field(default=None, alias="projectId")


class GroupRequest(StaffSchema):
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = Field(default=None, alias="projectId")


class GroupItem(StaffSchema):
    id: int
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = Field(default=None, alias="projectId")
    admin_id: Optional[int] = Field(default=None, alias="adminId")
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    updated_time: Optional[datetime] = Field(default=None, alias="updatedTime")
    joined: bool = False
    can_manage: bool = Field(default=False, alias="canManage")
    can_set_admin: bool = Field(default=False, alias="canSetAdmin")


class GroupDetail(StaffSchema):
    id: int
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = Field(default=None, alias="projectId")
    admin_id: Optional[int] = Field(default=None, alias="adminId")
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    member_count: int = Field(default=0, alias="memberCount")
