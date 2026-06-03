"""
Announcement model - SQLAlchemy ORM
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.session import Base


class Announcement(Base):
    """公告模型"""
    __tablename__ = "announcement"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    author_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)

    author = relationship("User")
    project = relationship("Project")

    @property
    def author_username(self):
        return getattr(self.author, "username", None) if self.author else None

    @property
    def author_display_name(self):
        if not self.author:
            return None
        first = getattr(self.author, "first_name", "") or ""
        last = getattr(self.author, "last_name", "") or ""
        full = f"{last}{first}".strip()
        return full or getattr(self.author, "username", None)

    def __repr__(self):
        return f"<Announcement(id={self.id}, title='{self.title}')>"
