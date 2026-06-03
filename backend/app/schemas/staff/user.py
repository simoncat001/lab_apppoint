"""Staff user DTOs — match Spring's User entity field-by-field."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.staff.common import BasePageRequest, StaffSchema


class LoginRequest(StaffSchema):
    username: str
    password: str


class RegisterRequest(StaffSchema):
    username: str
    password: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class StaffUserBase(StaffSchema):
    """Mirror of `User` entity returned to the UI. Password is never set."""

    id: Optional[int] = None
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    job_number: Optional[str] = Field(default=None, alias="jobNumber")
    status: Optional[int] = None
    created_time: Optional[datetime] = Field(default=None, alias="createdTime")
    updated_time: Optional[datetime] = Field(default=None, alias="updatedTime")


class StaffUserResponse(StaffUserBase):
    """Same as the base but explicit — used in responses."""


class UserUpsertRequest(StaffUserBase):
    """For POST/PUT /api/users — Spring accepts a raw User entity."""

    password: Optional[str] = None


class LoginResponse(StaffSchema):
    token: str
    user_info: StaffUserResponse = Field(alias="userInfo")


class UserQuery(BasePageRequest):
    """Matches `UserQueryDTO extends BasePageRequest` (keyword filter only)."""
