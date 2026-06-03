"""
Maintenance record model - SQLAlchemy ORM
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_record"

    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(Integer, ForeignKey("tool.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_due_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=False)

    tool = relationship("Tool")
    staff = relationship("User")
