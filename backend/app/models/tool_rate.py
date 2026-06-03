"""
Tool Rate model - SQLAlchemy ORM
"""
from typing import TYPE_CHECKING
from datetime import time

from sqlalchemy import Column, Integer, Time, ForeignKey, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.tool import Tool

class ToolRate(Base):
    """工具分时费率模型"""
    __tablename__ = "tool_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tool_id: Mapped[int] = mapped_column(Integer, ForeignKey("tool.id", ondelete="CASCADE"), index=True)
    
    start_time: Mapped[time] = mapped_column(Time, nullable=False, comment="开始时间")
    end_time: Mapped[time] = mapped_column(Time, nullable=False, comment="结束时间")
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, comment="该时段费率")
    
    # Relationship
    tool: Mapped["Tool"] = relationship("Tool", back_populates="rates")

    def __repr__(self):
        return f"<ToolRate(tool_id={self.tool_id}, {self.start_time}-{self.end_time}: {self.price})>"
