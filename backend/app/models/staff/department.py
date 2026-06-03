"""staff_department — ported from security-server `department` table."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text

from app.db.session import Base


class StaffDepartment(Base):
    __tablename__ = "staff_department"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
