from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnnouncementBase(BaseModel):
    title: str
    content: str
    published: bool = True


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None


class AnnouncementResponse(AnnouncementBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author_id: Optional[int] = None
    project_id: Optional[int] = None
    # 由 Announcement ORM 上的 @property 提供（见 models/announcement.py）
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None

    class Config:
        from_attributes = True
