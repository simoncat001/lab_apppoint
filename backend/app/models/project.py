"""
Project model - SQLAlchemy ORM
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class Project(Base):
    """项目模型"""
    __tablename__ = "project"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    application_identifier: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)
    
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # 项目信息
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    
    # 允许员工收费
    allow_staff_charges: Mapped[bool] = mapped_column(Boolean, default=False)
    # 是否允许外部用户申请该项目的预约权限（本地镜像元数据，不同步回权鉴）
    allow_external_booking_request: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # 权鉴项目配置的对外展示名称（用于外部用户申请页面展示）
    external_display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # 关系
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="projects")
    join_requests_as_source: Mapped[list["ProjectJoinRequest"]] = relationship(
        "ProjectJoinRequest",
        foreign_keys="ProjectJoinRequest.source_project_id",
        back_populates="source_project",
    )
    join_requests_as_target: Mapped[list["ProjectJoinRequest"]] = relationship(
        "ProjectJoinRequest",
        foreign_keys="ProjectJoinRequest.target_project_id",
        back_populates="target_project",
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class ProjectJoinRequest(Base):
    """用户申请加入项目（通过项目绑定账户成员关系实现）"""

    __tablename__ = "project_join_request"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_user_id])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_user_id])
    source_project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[source_project_id],
        back_populates="join_requests_as_source",
    )
    target_project: Mapped["Project"] = relationship(
        "Project",
        foreign_keys=[target_project_id],
        back_populates="join_requests_as_target",
    )

    def __repr__(self):
        return (
            f"<ProjectJoinRequest(id={self.id}, requester_user_id={self.requester_user_id}, "
            f"target_project_id={self.target_project_id}, status='{self.status}')>"
        )
