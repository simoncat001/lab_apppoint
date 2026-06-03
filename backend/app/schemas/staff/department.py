"""Staff department DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.staff.common import BasePageRequest, StaffSchema


class DepartmentQuery(BasePageRequest):
    """Mirrors `DepartmentQueryDTO` — only keyword + page."""


class MemberQuery(BasePageRequest):
    """Mirrors `MemberQueryDTO`."""


class DepartmentRequest(StaffSchema):
    """Body for POST /departments and PUT /departments/{id}."""

    name: str
    description: Optional[str] = None


class DepartmentItem(StaffSchema):
    """Returned by /departments/list — Spring's `Department` entity plus
    derived `joined` / `canManage` flags filled by the service."""

    id: int
    name: str
    description: Optional[str] = None
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    updated_time: Optional[datetime] = Field(default=None, alias="updatedTime")
    joined: bool = False
    can_manage: bool = Field(default=False, alias="canManage")


class DepartmentDetail(StaffSchema):
    """Mirror of `DepartmentDetailDTO`."""

    id: int
    name: str
    description: Optional[str] = None
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    member_count: int = Field(default=0, alias="memberCount")
    project_count: int = Field(default=0, alias="projectCount")


class OrganizationMember(StaffSchema):
    """Mirror of `OrganizationMemberDTO` (used by all member-list endpoints)."""

    user_id: int = Field(alias="userId")
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_admin: bool = Field(default=False, alias="isAdmin")


class ApplicationRequestPayload(StaffSchema):
    """Body sent to /api/departments/{id}/apply etc."""

    reason: Optional[str] = None
