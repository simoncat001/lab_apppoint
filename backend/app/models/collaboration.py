"""Research collaboration record model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.maintenance import MaintenanceRecord
    from app.models.project import Project
    from app.models.reservation import Reservation
    from app.models.task import Task
    from app.models.tool import Tool
    from app.models.usage_event import UsageEvent
    from app.models.user import User


class CollaborationRecord(Base):
    """Business-object-bound research collaboration record.

    The string fields intentionally avoid database ENUMs so the table remains
    portable across the project's current MySQL + aiomysql setup.
    """

    __tablename__ = "collaboration_record"
    __table_args__ = (
        Index("ix_collab_project_type_created", "project_id", "record_type", "created_at"),
        Index("ix_collab_tool_type_created", "tool_id", "record_type", "created_at"),
        Index("ix_collab_reservation_id", "reservation_id"),
        Index("ix_collab_author_created", "author_id", "created_at"),
        Index("ix_collab_status", "status"),
        Index("ix_collab_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    tool_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tool.id", ondelete="SET NULL"), nullable=True)
    reservation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reservation.id", ondelete="SET NULL"),
        nullable=True,
    )
    usage_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usage_event.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task.id", ondelete="SET NULL"), nullable=True)
    maintenance_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("maintenance_record.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    record_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(30), default="markdown", nullable=False)
    visibility: Mapped[str] = mapped_column(String(30), default="project", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship("Project")
    tool: Mapped[Optional["Tool"]] = relationship("Tool")
    reservation: Mapped[Optional["Reservation"]] = relationship("Reservation")
    usage_event: Mapped[Optional["UsageEvent"]] = relationship("UsageEvent")
    task: Mapped[Optional["Task"]] = relationship("Task")
    maintenance_record: Mapped[Optional["MaintenanceRecord"]] = relationship("MaintenanceRecord")
    author: Mapped["User"] = relationship("User")

    @property
    def author_username(self) -> Optional[str]:
        return getattr(self.author, "username", None) if self.author else None

    @property
    def author_display_name(self) -> Optional[str]:
        if not self.author:
            return None
        first = getattr(self.author, "first_name", "") or ""
        last = getattr(self.author, "last_name", "") or ""
        full = f"{last}{first}".strip()
        return full or getattr(self.author, "username", None)

    def __repr__(self) -> str:
        return f"<CollaborationRecord(id={self.id}, type='{self.record_type}', project_id={self.project_id})>"
