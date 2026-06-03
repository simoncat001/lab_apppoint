"""staff_group — ported from security-server `sys_group` table."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text, UniqueConstraint

from app.db.session import Base


class StaffGroup(Base):
    __tablename__ = "staff_group"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uk_staff_group_proj_name"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    project_id = Column(BigInteger, nullable=False, index=True)
    admin_id = Column(BigInteger, nullable=True)
    description = Column(Text, nullable=True)
    created_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
