"""staff_project — ported from security-server `project` table.

Includes V1.0.2 columns (external_visible, external_display_name) used by
the integrations/security_server_project_service.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from app.db.session import Base


class StaffProject(Base):
    __tablename__ = "staff_project"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uk_staff_project_dept_name"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department_id = Column(BigInteger, nullable=False, index=True)
    leader_id = Column(BigInteger, nullable=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(Integer, nullable=False, default=1)
    external_visible = Column(Boolean, nullable=False, default=False)
    external_display_name = Column(String(100), nullable=True)
    created_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
