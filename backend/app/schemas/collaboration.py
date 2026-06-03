"""Pydantic schemas for research collaboration records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


CollaborationRecordType = Literal[
    "tool_note",
    "reservation_note",
    "experiment_note",
    "maintenance_experience",
    "sop",
    "faq",
    "case_study",
    "issue",
]
CollaborationVisibility = Literal["project", "staff", "tool_managers", "author_private"]
CollaborationStatus = Literal["draft", "published", "archived"]


class CollaborationRecordBase(BaseModel):
    tool_id: Optional[int] = None
    reservation_id: Optional[int] = None
    record_type: CollaborationRecordType
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    content_format: str = Field("markdown", min_length=1, max_length=30)
    visibility: CollaborationVisibility = "project"
    status: CollaborationStatus = "draft"


class CollaborationRecordCreate(CollaborationRecordBase):
    pass


class CollaborationRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    content_format: Optional[str] = Field(None, min_length=1, max_length=30)
    visibility: Optional[CollaborationVisibility] = None
    status: Optional[CollaborationStatus] = None
    pinned: Optional[bool] = None


class CollaborationRecordResponse(BaseModel):
    id: int
    project_id: int
    tool_id: Optional[int] = None
    reservation_id: Optional[int] = None
    usage_event_id: Optional[int] = None
    task_id: Optional[int] = None
    maintenance_record_id: Optional[int] = None
    author_id: int
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None
    record_type: str
    title: str
    content: str
    content_format: str
    visibility: str
    status: str
    pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
