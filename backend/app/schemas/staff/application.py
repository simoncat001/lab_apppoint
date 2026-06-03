"""Staff application-request DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.staff.common import BasePageRequest, StaffSchema


class ApplicationQuery(BasePageRequest):
    status: Optional[int] = None
    target_type: Optional[int] = Field(default=None, alias="targetType")
    target_id: Optional[int] = Field(default=None, alias="targetId")
    audit_only: Optional[bool] = Field(default=None, alias="auditOnly")


class ApplicationSubmitRequest(StaffSchema):
    target_type: int = Field(alias="targetType")
    target_id: int = Field(alias="targetId")
    reason: Optional[str] = None


class ApproveRequest(StaffSchema):
    approver_comment: Optional[str] = Field(default=None, alias="approverComment")


class RejectRequest(StaffSchema):
    reject_reason: Optional[str] = Field(default=None, alias="rejectReason")


class ApplicationItem(StaffSchema):
    id: int
    user_id: int = Field(alias="userId")
    target_type: int = Field(alias="targetType")
    target_id: int = Field(alias="targetId")
    status: int
    reason: Optional[str] = None
    approver_id: Optional[int] = Field(default=None, alias="approverId")
    approve_result: Optional[int] = Field(default=None, alias="approveResult")
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    applicant_name: Optional[str] = Field(default=None, alias="applicantName")
    target_name: Optional[str] = Field(default=None, alias="targetName")
