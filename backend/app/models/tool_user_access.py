"""
Tool-User access control model.

Grants specific external users access to restricted tools.
When a tool has restrict_external_access=True, only users with
an entry in this table can view/reserve that tool.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ToolUserAccess(Base):
    """设备级用户访问权限"""
    __tablename__ = "tool_user_access"
    __table_args__ = (
        UniqueConstraint("tool_id", "user_id", name="uq_tool_user_access"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tool_id = Column(Integer, ForeignKey("tool.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime, default=func.now(), nullable=False)

    tool = relationship("Tool", back_populates="authorized_users")
    user = relationship("User", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])
