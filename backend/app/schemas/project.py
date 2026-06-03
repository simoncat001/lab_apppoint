"""
Project Pydantic schemas
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.user import UserBasic


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    application_identifier: Optional[str] = Field(None, max_length=200)
    active: bool = True


class ProjectCreate(ProjectBase):
    """创建项目"""
    application_identifier: str = Field(..., min_length=1, max_length=200)
    account_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    """更新项目"""
    name: Optional[str] = None
    active: Optional[bool] = None
    account_id: Optional[int] = None


class ProjectInDB(ProjectBase):
    """数据库中的项目"""
    id: int
    start_date: Optional[datetime] = None
    account_id: Optional[int] = None
    allow_external_booking_request: bool = False
    external_display_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class Project(ProjectInDB):
    """返回给客户端的项目"""
    pass


class ProjectExternalBookingAccessUpdate(BaseModel):
    allow_external_booking_request: bool = Field(..., description="是否对外开放项目预约权限申请")


class ProjectJoinRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ProjectJoinRequestCreate(BaseModel):
    target_project_id: int = Field(..., gt=0, description="目标项目ID")
    reason: Optional[str] = Field(None, max_length=2000, description="申请说明")


class ProjectJoinRequestReview(BaseModel):
    comment: Optional[str] = Field(None, max_length=2000, description="审批备注")


class ProjectJoinRequestResponse(BaseModel):
    id: int
    requester_user_id: int
    source_project_id: Optional[int] = None
    target_project_id: int
    status: ProjectJoinRequestStatus
    reason: Optional[str] = None
    review_comment: Optional[str] = None
    reviewer_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    requester: Optional[UserBasic] = None
    reviewer: Optional[UserBasic] = None
    source_project: Optional[Project] = None
    target_project: Optional[Project] = None

    class Config:
        from_attributes = True
