from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.tool import Tool
    from app.models.user import User


class TaskUrgency(IntEnum):
    """任务紧急程度"""
    LOW = -1
    NORMAL = 0
    HIGH = 1


class TaskCategoryStage(IntEnum):
    """任务分类阶段"""
    INITIAL_ASSESSMENT = 0
    COMPLETION = 1


class TaskCategory(Base):
    """任务分类"""
    __tablename__ = "task_category"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    stage: Mapped[int] = mapped_column(Integer)  # TaskCategoryStage

    # 关系
    problem_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.problem_category_id",
        back_populates="problem_category"
    )
    resolution_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.resolution_category_id",
        back_populates="resolution_category"
    )

    def __repr__(self):
        return f"<TaskCategory(id={self.id}, name='{self.name}')>"


class Task(Base):
    """任务/工单模型"""
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 外键
    tool_id: Mapped[int] = mapped_column(
        ForeignKey("tool.id", ondelete="CASCADE"),
        index=True
    )
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    last_updated_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )
    resolver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )
    problem_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task_category.id", ondelete="SET NULL"),
        nullable=True
    )
    resolution_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task_category.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # 状态字段
    urgency: Mapped[int] = mapped_column(Integer, index=True)  # TaskUrgency
    force_shutdown: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    safety_hazard: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # 时间字段
    creation_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estimated_resolution_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    resolution_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 文本字段
    problem_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系
    tool: Mapped["Tool"] = relationship("Tool")
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    last_updated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[last_updated_by_id]
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[resolver_id]
    )
    problem_category: Mapped[Optional["TaskCategory"]] = relationship(
        "TaskCategory",
        foreign_keys=[problem_category_id],
        back_populates="problem_tasks"
    )
    resolution_category: Mapped[Optional["TaskCategory"]] = relationship(
        "TaskCategory",
        foreign_keys=[resolution_category_id],
        back_populates="resolution_tasks"
    )
    history: Mapped[List["TaskHistory"]] = relationship(
        "TaskHistory",
        back_populates="task",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Task(id={self.id}, tool_id={self.tool_id}, urgency={self.urgency})>"

    @property
    def status_display(self) -> str:
        """获取任务状态显示文本"""
        if self.cancelled:
            return "Cancelled"
        elif self.resolved:
            return "Resolved"
        else:
            return "Open"


class TaskHistory(Base):
    """任务历史记录"""
    __tablename__ = "task_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 外键
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"),
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True
    )
    
    # 字段
    status: Mapped[str] = mapped_column(String(200))
    time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    task: Mapped["Task"] = relationship("Task", back_populates="history")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<TaskHistory(id={self.id}, task_id={self.task_id}, status='{self.status}')>"
