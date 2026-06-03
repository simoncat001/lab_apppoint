"""
Tool image model - SQLAlchemy ORM
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.tool import Tool


class ToolImage(Base):
    """仪器图片模型"""

    __tablename__ = "tool_image"
    __table_args__ = (
        UniqueConstraint("tool_id", "path", name="uq_tool_image_tool_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tool_id: Mapped[int] = mapped_column(Integer, ForeignKey("tool.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tool: Mapped["Tool"] = relationship("Tool", back_populates="images")

    def __repr__(self) -> str:
        return f"<ToolImage(id={self.id}, tool_id={self.tool_id}, path='{self.path}')>"
